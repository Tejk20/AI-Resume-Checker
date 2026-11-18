"""Measured, label-free MiniLM/MPNet comparison on the same section-aware pipeline.
Each model runs in a fresh subprocess to separate RSS measurements. No live DB
or personal candidate files are used. Run from project root after model download.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace as NS
from threading import Event, Thread

ROOT = Path(__file__).resolve().parents[1]
MODELS = {'minilm':'sentence-transformers/all-MiniLM-L6-v2', 'mpnet':'sentence-transformers/all-mpnet-base-v2'}


def measure_model(label, output):
    os.chdir(ROOT/'backend')
    sys.path.insert(0,str(ROOT/'backend'))
    import numpy as np
    from app.services.documents import extract_document
    from app.services.extraction import parse_job, parse_resume
    from app.services.semantic import SemanticEvaluation, VECTOR_CACHE
    from app.services.scoring import score_candidate
    from app.core.config import WEIGHTS, ALGORITHM_VERSION
    candidates=[]
    for path in sorted((ROOT/'sample_data/synthetic_resumes').iterdir()):
        if path.suffix in {'.pdf','.docx'}:
            text,_=extract_document(path.name,path.read_bytes())
            candidates.append(NS(**parse_resume(text)))
    jobs=[]
    for path in sorted((ROOT/'sample_data/job_descriptions').glob('*.txt')):
        text=path.read_text()
        jobs.append((path.stem,NS(title={'ai_ml':'AI/ML Engineer','python_backend':'Python Backend Developer','react_fullstack':'React Full Stack Developer'}[path.stem],raw_text=text,**parse_job(text))))
    memory={'baseline_rss_mb':None,'peak_rss_mb':None}
    stop=Event()
    try:
        import psutil
        process=psutil.Process()
        memory['baseline_rss_mb']=process.memory_info().rss/1024**2
        memory['peak_rss_mb']=memory['baseline_rss_mb']
        def sample():
            while not stop.wait(.05):
                memory['peak_rss_mb']=max(memory['peak_rss_mb'],process.memory_info().rss/1024**2)
        thread=Thread(target=sample,daemon=True);thread.start()
    except ImportError:
        process=None
    report={'model':MODELS[label],'algorithm_version':ALGORITHM_VERSION,'default_weights':WEIGHTS,'jobs':[]}
    started=time.perf_counter()
    for index,(slug,job) in enumerate(jobs):
        start=time.perf_counter()
        evaluation=SemanticEvaluation(job,MODELS[label])
        if index==0: report['initialization_seconds']=round(time.perf_counter()-start,4)
        inference_start=time.perf_counter()
        prepared=evaluation.prepare_many(candidates)
        rows=[]
        for candidate,item in zip(candidates,prepared):
            semantic,evidence=evaluation.compare_prepared(item)
            score=score_candidate(job,candidate,semantic,evidence)
            rows.append({'candidate':candidate.name,'semantic_score':semantic,'overall_score':score['overall_score'],
                         'missing_required':score['explanation']['missing_required']})
        elapsed=time.perf_counter()-inference_start
        rows.sort(key=lambda item:(-item['overall_score'],item['candidate']))
        for rank,row in enumerate(rows,1):row['rank']=rank
        misses=VECTOR_CACHE.misses
        warm_start=time.perf_counter()
        again=evaluation.prepare_many(candidates)
        for candidate,item in zip(candidates,again):
            semantic,evidence=evaluation.compare_prepared(item)
            original=next(row for row in rows if row['candidate']==candidate.name)
            assert semantic==original['semantic_score']
        warm=time.perf_counter()-warm_start
        assert VECTOR_CACHE.misses==misses,'Warm repeat unnecessarily generated new embeddings'
        assert all(0<=r['overall_score']<=100 and 0<=r['semantic_score']<=100 for r in rows)
        report['jobs'].append({'job':slug,'matching_seconds':round(elapsed,4),'warm_seconds':round(warm,4),'rankings':rows})
        report['semantic_metadata']=evaluation.metadata
    report['total_seconds']=round(time.perf_counter()-started,4)
    report['cache_hits']=VECTOR_CACHE.hits;report['cache_misses']=VECTOR_CACHE.misses
    stop.set()
    if process:
        thread.join();memory['final_rss_mb']=process.memory_info().rss/1024**2
        memory['peak_rss_mb']=max(memory['peak_rss_mb'],memory['final_rss_mb'])
        memory['peak_increase_mb']=memory['peak_rss_mb']-memory['baseline_rss_mb']
    report['memory']={key:round(value,2) if value is not None else None for key,value in memory.items()}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2))
    print(label, 'comparison complete:',report['total_seconds'],'seconds;',report['memory'],flush=True)


def compare():
    artifacts=ROOT/'test-artifacts';artifacts.mkdir(exist_ok=True)
    environment={**os.environ,'HF_HUB_OFFLINE':'1','TOKENIZERS_PARALLELISM':'false'}
    for label in MODELS:
        subprocess.run([sys.executable,__file__,'--model',label,'--output',str(artifacts/f'{label}-comparison.json')],env=environment,check=True)
    first=json.loads((artifacts/'minilm-comparison.json').read_text())
    second=json.loads((artifacts/'mpnet-comparison.json').read_text())
    lines=['# MiniLM and MPNet: measured comparison','','Both models use algorithm 2.0.0, identical section-aware retrieval, the same 12 synthetic PDF/DOCX resumes, three JDs, and 25/40/25/10 scoring weights. This isolates the embedding-model change; it is not a comparison against the old unsectioned pipeline. No recruiter-reviewed relevance labels exist, so these measurements do **not** establish accuracy or hiring quality.','','## Timing and memory','','CPU only. Model weights were already cached locally. Fresh subprocess per model. Initialization includes library import and model load; matching excludes initialization. RSS is process memory sampled every 50 ms, not GPU memory or a guaranteed operating-system high-water mark. Timing and memory may vary with system load.','','| Model | Dimensions | Input token limit | Initialization s | Total benchmark s | Sampled peak RSS MB | Peak increase MB |','|---|---:|---:|---:|---:|---:|---:|']
    for label,report in [('MiniLM',first),('MPNet',second)]:
        meta=report['semantic_metadata'];memory=report['memory']
        lines.append(f"| {label} | {meta['embedding_dimensions']} | {meta['max_sequence_tokens']} | {report['initialization_seconds']} | {report['total_seconds']} | {memory['peak_rss_mb']} | {memory.get('peak_increase_mb')} |")
    lines+=['','## Per-job results','','Rank changes are descriptive differences, not validated improvements. Warm timings reuse cached vectors.','','| Job | MiniLM first candidate / score | MPNet first candidate / score | MiniLM matching / warm s | MPNet matching / warm s | Candidates changing rank | Mean semantic change (MPNet - MiniLM) |','|---|---|---|---|---|---:|---:|']
    differences=[]
    for a,b in zip(first['jobs'],second['jobs']):
        mini={r['candidate']:r for r in a['rankings']}
        rows=[]
        for row in b['rankings']:
            baseline=mini[row['candidate']]
            rows.append({'candidate':row['candidate'],'minilm_rank':baseline['rank'],'mpnet_rank':row['rank'],
                'minilm_semantic':baseline['semantic_score'],'mpnet_semantic':row['semantic_score'],
                'semantic_difference':round(row['semantic_score']-baseline['semantic_score'],2),
                'minilm_overall':baseline['overall_score'],'mpnet_overall':row['overall_score']})
            assert row['missing_required']==baseline['missing_required'],'Model change altered exact mandatory-skill matching'
        changed=sum(r['minilm_rank']!=r['mpnet_rank'] for r in rows)
        mean=sum(r['semantic_difference'] for r in rows)/len(rows)
        x,y=a['rankings'][0],b['rankings'][0]
        lines.append(f"| {a['job']} | {x['candidate']} / {x['overall_score']} | {y['candidate']} / {y['overall_score']} | {a['matching_seconds']} / {a['warm_seconds']} | {b['matching_seconds']} / {b['warm_seconds']} | {changed} | {mean:+.2f} |")
        differences.append({'job':a['job'],'rank_changes':changed,'candidates':rows})
    for item in differences:
        lines+=['',f"## {item['job']}: individual differences",'','| Candidate | MiniLM rank | MPNet rank | MiniLM semantic | MPNet semantic | Semantic change | MiniLM overall | MPNet overall |','|---|---:|---:|---:|---:|---:|---:|---:|']
        for row in item['candidates']:
            lines.append('| '+ ' | '.join(str(row[key]) for key in ['candidate','minilm_rank','mpnet_rank','minilm_semantic','mpnet_semantic','semantic_difference','minilm_overall','mpnet_overall'])+' |')
    lines+=['','## Regression checks and limitations','','Both models returned bounded scores and deterministic warm-cache repeats. Mandatory missing-skill lists remained identical across models. MPNet is not assumed more accurate because it is larger. Meaningful accuracy evaluation needs recruiter-reviewed relevance judgments and a larger representative dataset. Model changes can raise or lower semantic scores; the compatibility scale is not calibrated as a probability. Full machine-readable outputs are in ignored test-artifacts/; this report contains only fictional identities.','']
    (ROOT/'docs/model-comparison.md').write_text('\n'.join(lines),encoding='utf-8')
    (artifacts/'model-differences.json').write_text(json.dumps(differences,indent=2))
    print('Saved docs/model-comparison.md and test-artifacts/model-differences.json')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--model',choices=list(MODELS));parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.model: measure_model(args.model,args.output)
    else: compare()
