"""Closed project-scoped annotation and paired experiment commands."""
from typing import Literal,Any
from pydantic import BaseModel,ConfigDict,Field
from html_reference_localization import MappedLocations

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')

class EvaluationRead(Strict):pass

class Sample(Strict):
    slide_id:str=Field(pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,100}$')
    course_id:str=Field(min_length=1,max_length=100)
    split:Literal['development','holdout']

class CreateDataset(Strict):
    action:Literal['create_dataset']
    dataset_id:str=Field(pattern=r'^[a-z][a-z0-9-]{0,63}$')
    samples:list[Sample]=Field(min_length=1,max_length=40)

class ReadCase(Strict):
    action:Literal['read_case']
    dataset_id:str=Field(pattern=r'^[a-z][a-z0-9-]{0,63}$')
    case_id:str=Field(pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,100}$')

class SaveLabels(Strict):
    action:Literal['save_labels']
    dataset_id:str=Field(pattern=r'^[a-z][a-z0-9-]{0,63}$')
    case_id:str=Field(pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,100}$')
    expected_revision:int=Field(ge=0,strict=True)
    source_sha256:str=Field(pattern=r'^[0-9a-f]{64}$')
    annotator:str=Field(min_length=1,max_length=100)
    mapping:MappedLocations

class ReviewLabels(Strict):
    action:Literal['review_labels']
    dataset_id:str=Field(pattern=r'^[a-z][a-z0-9-]{0,63}$')
    case_id:str=Field(pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,100}$')
    expected_revision:int=Field(ge=1,strict=True)
    source_sha256:str=Field(pattern=r'^[0-9a-f]{64}$')
    reviewer:str=Field(min_length=1,max_length=100)
    decision:Literal['accept','reject']
    note:str=Field(min_length=8,max_length=1000)

class Arm(Strict):
    model_role:Literal['text','planning']='text'
    protocol:Literal['0.5.0','0.5.1']='0.5.1'

class StartExperiment(Strict):
    action:Literal['start_experiment']
    dataset_id:str=Field(pattern=r'^[a-z][a-z0-9-]{0,63}$')
    before:Arm=Field(default_factory=lambda:Arm(protocol='0.5.0'))
    after:Arm=Field(default_factory=Arm)
    repetitions:int=Field(default=1,ge=1,le=5,strict=True)
    max_model_calls:int=Field(default=8,ge=2,le=128,strict=True)
    max_http_calls:int=Field(default=12,ge=2,le=256,strict=True)
    total_seconds:int=Field(default=1800,ge=60,le=7200,strict=True)
    request_seconds:int=Field(default=600,ge=30,le=600,strict=True)

class EvaluationCommand(Strict):
    command:CreateDataset|ReadCase|SaveLabels|ReviewLabels|StartExperiment=Field(discriminator='action')

class EvaluationResult(BaseModel):
    project_id:str
    evaluation:dict[str,Any]
