from types import SimpleNamespace as NS
import pytest
from app.services.scoring import weighted_score,skill_coverage,score_candidate,relevant_experience
from app.services.extraction import parse_resume


def job(**kwargs):
    return NS(title='Python Backend Developer',required_skills=kwargs.get('required_skills',['Python','FastAPI']),preferred_skills=kwargs.get('preferred_skills',[]),min_experience=kwargs.get('min_experience',3),qualifications=kwargs.get('qualifications',[]))


def candidate(text):return NS(**parse_resume(text))


def test_weighted_manual_calculation():
    score,weights,contributions=weighted_score(dict(semantic=80,skill=90,experience=75,education=100))
    assert score==84.75
    assert weights=={'semantic':.25,'skill':.40,'experience':.25,'education':.10}
    assert contributions=={'semantic':20,'skill':36,'experience':18.75,'education':10}
    assert sum(weights.values())==pytest.approx(1)
    assert sum(contributions.values())==pytest.approx(score)


def test_redistribution_and_no_skills():
    score,w,c=weighted_score(dict(semantic=80,skill=100,experience=None,education=None))
    assert score==92.31
    assert w==pytest.approx({'semantic':.25/.65,'skill':.40/.65})
    assert skill_coverage([],[],[]) is None
    assert skill_coverage(['Python'],[],['Python'])==100
    assert skill_coverage([],['AWS'],[])==0


def test_unknown_is_provisional_not_inapplicable():
    result=score_candidate(job(),candidate('Finley Grey\nSkills\nPython\nProjects\nPersonal learning work.'),70,[])
    assert result['experience_score']==50
    assert result['explanation']['relevant_years'] is None
    assert 'experience' in result['explanation']['weights']
    assert result['explanation']['review_required']
    assert any('provisional' in w for w in result['explanation']['warnings'])


def test_relevance_and_internships():
    c=candidate('Alex Rowan\nExperience\nJava Engineer Jan 2018 - Jan 2022\nBuilt Java systems.\nPython Engineer Jan 2022 - Jan 2024\nDeveloped Python FastAPI services.\nPython Intern Jan 2016 - Jan 2018\nPython FastAPI training.\nEducation\nBachelor of Computer Science')
    years,roles=relevant_experience(job(),c)
    assert years==2
    assert len(roles)==1


def test_deterministic_bounded_and_strong_above_weak():
    c=candidate('Alex Rowan\nSkills\nPython FastAPI\nExperience\nPython Engineer Jan 2020 - Jan 2025\nBuilt Python FastAPI services.\nEducation\nBachelor of Computer Science')
    j=job(qualifications=['Bachelor degree in Computer Science'])
    strong=score_candidate(j,c,85,[])
    weak=score_candidate(j,candidate('Drew Elm\nSkills\nJava MySQL\nExperience\nJava Engineer Jan 2020 - Jan 2025\nJava MySQL systems.\nEducation\nDiploma in Design'),30,[])
    assert 0<=weak['overall_score']<strong['overall_score']<=100
    assert strong==score_candidate(j,c,85,[])
    assert strong['education_score']==100 and weak['education_score']==0


def test_inapplicable_components():
    j=job(min_experience=None,qualifications=[],required_skills=[],preferred_skills=[])
    result=score_candidate(j,candidate('Alex Rowan\nProjects\nBuilt a learning portfolio.'),66,[])
    assert result['overall_score']==66
    assert result['explanation']['weights']=={'semantic':1.0}


def test_degree_does_not_confirm_a_combined_certification_requirement():
    j=job(qualifications=['Bachelor degree and AWS certification required'])
    c=candidate('Alex Rowan\nSkills\nPython\nEducation\nBachelor of Computer Science')
    result=score_candidate(j,c,70,[])
    assert result['education_score']==50
    assert result['explanation']['review_required']
