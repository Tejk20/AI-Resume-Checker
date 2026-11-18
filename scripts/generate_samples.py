"""All names, employers, and contact details below are fictional."""
from pathlib import Path
import fitz
from docx import Document

ROOT=Path(__file__).resolve().parents[1]/'sample_data'
JOBS={
 'python_backend':('Python Backend Developer','We are looking for a Python Backend Developer with at least 3 years of experience.\nRequired skills: Python, FastAPI, PostgreSQL, REST APIs, Docker.\nAWS knowledge is preferred.\nBuild reliable REST APIs and optimize relational database queries.\nDesign backend services and deploy containerized applications.\nBachelor degree in Computer Science or equivalent experience.'),
 'react_fullstack':('React Full Stack Developer','React Full Stack Developer with at least 2 years of experience.\nRequired skills: ReactJS, JavaScript, NodeJS, HTML, CSS, RESTful APIs.\nTypeScript and PostgreSQL preferred.\nBuild accessible responsive interfaces and integrate web APIs.\nDevelop frontend components and backend services.\nBachelor degree in Computer Science or equivalent experience.'),
 'ai_ml':('AI/ML Engineer','AI/ML Engineer with at least 2 years of experience.\nRequired skills: Python, PyTorch, scikit-learn, NLP, pandas, NumPy.\nSentence Transformers and Docker preferred.\nTrain and evaluate machine learning models and build NLP pipelines.\nDevelop semantic search with sentence embeddings.\nMaster degree in Computer Science or equivalent experience.')}
PROFILES=[
 ('Alex Rowan','Backend Developer','Python, FastAPI, PostgreSQL, RESTful APIs, Docker, AWS','Jan 2021','Jan 2026','Built reliable REST APIs using Python and FastAPI. Optimized PostgreSQL queries and deployed Docker services to AWS.','Bachelor of Computer Science'),
 ('Morgan Vale','Python Engineer','Python3, FastAPI, Postgres, REST API, Docker, pytest','Jan 2022','Jan 2026','Developed Python backend services and FastAPI endpoints with PostgreSQL and Docker.','Bachelor of Computer Science'),
 ('Casey Brook','Backend Developer','Python, Django, MySQL, REST API','Jan 2023','Jan 2025','Built Django web services in Python with MySQL. Implemented REST API authentication.','Bachelor of Computer Science'),
 ('Riley Fern','React Developer','ReactJS, JavaScript, NodeJS, HTML, CSS, RESTful APIs, TypeScript, PostgreSQL','Jan 2020','Jan 2026','Built accessible responsive React interfaces in JavaScript and TypeScript. Developed Node.js backend services and REST APIs.','Bachelor of Computer Science'),
 ('Jordan Pine','Full Stack Developer','React, JavaScript, Node.js, HTML, CSS, REST API','Jan 2022','Jan 2026','Developed React components and Node.js services. Built accessible web interfaces using HTML and CSS and integrated REST APIs.','Bachelor of Software Engineering'),
 ('Taylor Ash','Frontend Developer','React, JavaScript, HTML, CSS','Jan 2024','Jan 2025','Built responsive frontend React components using JavaScript, HTML and CSS.','Diploma in Web Design'),
 ('Avery Reed','ML Engineer','Python, PyTorch, scikit-learn, NLP, pandas, NumPy, Sentence Transformers, Docker','Jan 2020','Jan 2026','Trained and evaluated PyTorch and scikit-learn models. Built NLP semantic search pipelines using Sentence Transformers, Python, pandas and NumPy.','Master of Computer Science'),
 ('Quinn Lake','Data Scientist','Python, scikit-learn, pandas, NumPy, NLP','Jan 2022','Jan 2026','Developed Python NLP classification pipelines and evaluated scikit-learn models using pandas and NumPy.','Master of Statistics'),
 ('Cameron Moss','ML Engineer','Python, TensorFlow, pandas, NumPy, Machine Learning','Jan 2023','Jan 2025','Trained TensorFlow machine learning models and cleaned data in Python with pandas and NumPy.','Bachelor of Mathematics'),
 ('Drew Elm','Java Developer','Java, Spring Boot, MySQL, Docker','Jan 2019','Jan 2026','Developed enterprise Java services with Spring Boot and MySQL, deployed through Docker.','Bachelor of Information Technology'),
 ('Skyler Wren','Designer','HTML, CSS','Jan 2024','Jan 2025','Created visual design systems and brand illustrations for fictional retail clients.','Bachelor of Fine Arts'),
 ('Finley Grey','Candidate','Python, React','','','Built a learning project; employment dates and qualifications not supplied.','')]


def pdf(path,lines):
    doc=fitz.open(); page=doc.new_page(); y=55
    for line in lines:
        import textwrap
        for wrapped in textwrap.wrap(line,90) or ['']:
            if y>780: page=doc.new_page(); y=55
            page.insert_text((45,y),wrapped,fontsize=10); y+=16
    doc.save(path);doc.close()


def main():
    resumes=ROOT/'synthetic_resumes'; jobs=ROOT/'job_descriptions'
    resumes.mkdir(parents=True,exist_ok=True);jobs.mkdir(parents=True,exist_ok=True)
    for slug,(title,text) in JOBS.items():
        (jobs/(slug+'.txt')).write_text(text,encoding='utf-8')
        pdf(jobs/(slug+'.pdf'),[title,*text.splitlines()])
    for i,(name,role,skills,start,end,description,education) in enumerate(PROFILES):
        contact=f'{name.lower().replace(" ",".")}@example.test'
        heading=['Work Experience','Professional Experience','Employment'][i%3]
        jobline=f'{role} | Fictional Orbit Labs | {start} - {end}' if start else role
        lines=[name,contact,'Summary',f'{role} focused on practical software delivery.','Technical Skills',skills,heading,jobline,description]
        if education: lines+=['Education',education]
        lines+=['Projects',f'Synthetic portfolio project: {description}','Certifications','No certification claimed.']
        # Alternate a skills-first and experience-first layout.
        if i%3==1: lines=lines[:2]+lines[6:]+lines[2:6]
        stem=f'{i+1:02d}_{name.lower().replace(" ","_")}'
        if i%2==0: pdf(resumes/(stem+'.pdf'),lines)
        else:
            doc=Document()
            for j,line in enumerate(lines):
                if j==0: doc.add_heading(line,0)
                elif line in ['Summary','Technical Skills',heading,'Education','Projects','Certifications']: doc.add_heading(line,1)
                else: doc.add_paragraph(line)
            doc.save(resumes/(stem+'.docx'))
    (ROOT/'README.md').write_text('All 12 candidate identities, employers and contact details are synthetic. Six PDF and six DOCX resumes cover backend, frontend, ML and unrelated roles. Finley has incomplete evidence. Generate again with python scripts/generate_samples.py. Never replace these with real candidate data in Git.\n',encoding='utf-8')
    print('Generated 12 synthetic resumes (6 PDF, 6 DOCX), 3 text JDs and 3 PDF JDs.')


if __name__=='__main__': main()
