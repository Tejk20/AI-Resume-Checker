from io import BytesIO
import pytest
import fitz
from docx import Document
from app.services.documents import extract_document, DocumentError, safe_filename
from app.services.skills import extract_skills
from app.services.extraction import parse_job, parse_resume, employment, union_years, month_index


@pytest.mark.parametrize('phrase,canonical',[('Python3','Python'),('ReactJS','React'),('RESTful API','REST API'),('PostgreSQL DB','PostgreSQL'),('NodeJS','Node.js'),('Scikit Learn','scikit-learn')])
def test_aliases(phrase,canonical):
    assert canonical in extract_skills(phrase)


@pytest.mark.parametrize('text,absent',[('JavaScript','Java'),('Django','FastAPI'),('MySQL','PostgreSQL'),('React Native','React'),('Azure','AWS'),('Pythonic','Python'),('JSmith','JavaScript')])
def test_distinct_skills(text,absent):
    assert absent not in extract_skills(text)


def test_job_context():
    job=parse_job("Python developer with at least 3 years of experience.\nRequired: Python, FastAPI, PostgreSQL, REST APIs, Docker.\nAWS knowledge is preferred.\nBachelor degree in Computer Science or equivalent experience.")
    assert set(job['required_skills'])=={'Python','FastAPI','PostgreSQL','REST API','Docker'}
    assert job['preferred_skills']==['AWS']
    assert job['min_experience']==3
    assert job['qualifications']


def test_overlap_dates_and_projects():
    text='Alex Rowan\nalex@example.test\nWork Experience\nEngineer Jan 2020 - Jan 2023\nBuilt Python APIs.\nEngineer Jan 2022 - Jan 2024\nBuilt FastAPI applications.\nProjects\nStudent work Jan 2015 - Jan 2020\nEducation\nBachelor of Computer Science'
    parsed=parse_resume(text)
    assert parsed['experience_years']==4
    assert parsed['name']=='Alex Rowan'
    assert parsed['projects']
    assert union_years([(0,24),(12,36)])==3


def test_unknown_and_uncertain_dates():
    parsed=parse_resume('Technical Skills\nPython\nProjects\nStudent project, 2018 - 2024')
    assert parsed['name'] is None and parsed['experience_years'] is None
    roles,warnings=employment(['Developer 2020 - 2022','Python backend'])
    assert roles[0]['uncertain'] and warnings
    with pytest.raises(ValueError): month_index('13/2020')


def test_pdf_and_docx():
    pdf=fitz.open();page=pdf.new_page();page.insert_text((40,50),'Alex Rowan - Python FastAPI developer with relevant experience.')
    data=pdf.tobytes();pdf.close()
    assert 'Alex Rowan' in extract_document('resume.pdf',data)[0]
    doc=Document();doc.add_paragraph('Morgan Vale - React and JavaScript developer with web experience.')
    buf=BytesIO();doc.save(buf)
    assert 'Morgan Vale' in extract_document('resume.docx',buf.getvalue())[0]


@pytest.mark.parametrize('name,data',[('r.exe',b'code'),('r.pdf',b'broken'),('r.docx',b'PKinvalid')])
def test_bad_documents(name,data):
    with pytest.raises(DocumentError):extract_document(name,data)


def test_empty_scanned_pdf():
    doc=fitz.open();doc.new_page();data=doc.tobytes();doc.close()
    with pytest.raises(DocumentError,match='OCR'):extract_document('scan.pdf',data)
    assert safe_filename('../../private\\resume.pdf')=='resume.pdf'


def test_explicit_demographics_do_not_become_skill_evidence():
    from app.services.privacy import scoring_text
    text='Alex Rowan\nNationality: Java\nReligion: Go\nGender: female\nAge: 25\nSkills: Python'
    candidate=parse_resume(text)
    assert candidate['skills']==['Python']
    clean=scoring_text(text,['Alex Rowan'])
    assert 'Alex Rowan' not in clean and 'female' not in clean and 'Nationality' not in clean
