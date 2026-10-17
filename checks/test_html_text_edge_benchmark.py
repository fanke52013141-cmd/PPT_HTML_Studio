"""Synthetic labels test metrics only; these are not real human annotations."""
import copy
import json
import shutil
import subprocess

from PIL import Image, ImageDraw
import pytest

from artifact_fingerprint import sha256_file, sha256_json
from html_text_edge_benchmark import POLICY, LABELER, prepare, score


def metric_fixture():
    samples=[];predictions=[];rows=[]
    for index,status in enumerate(('possible_clip','possible_clip','no_detected_clip','no_detected_clip','uncertain','uncertain')):
        sample={'case_id':str(index//2),'reference_sha256':'same-image','result_sha256':'record',
                'targetId':'t','partId':'title','region_index':index,'proposed_bounds':[20,20,80,40],
                'image_size':[100,60],'text':'synthetic'}
        sample['sample_id']=sha256_json(sample);samples.append(sample)
        predictions.append({'sample_id':sample['sample_id'],'status':status})
        clipped=index%2==0
        rows.append({'sample_id':sample['sample_id'],'label':'clipped' if clipped else 'complete',
                     'truth_bounds':[19 if clipped else 21,21,79,39],'active_review_ms':1000})
    package={'policy':POLICY,'samples':samples,'predictions_sha256':sha256_json(predictions)}
    annotations={'policy':POLICY,'package_sha256':sha256_json(package),'reviewer_id':'synthetic-test-only',
                 'declared_human_blind_review':True,'timing_protocol':'foreground_explicit_start/0.1.0','rows':rows}
    return package,annotations,{'package_sha256':sha256_json(package),'regions':predictions}


def test_metrics_report_abstentions_and_real_denominators_separately():
    package,annotations,predictions=metric_fixture()
    result=score(package,annotations,predictions)
    assert result['decisive']=={'tp':1,'fp':1,'fn':1,'tn':1,'precision':.5,
        'false_positive_rate':.5,'false_negative_rate':.5,'coverage':4/6}
    assert result['abstentions']=={'clipped':1,'complete':1}
    assert result['alarm_recall']==1/3 and result['review_routing_recall']==2/3
    assert result['unique_reference_images']==1 and result['case_count']==3
    assert result['timing']['total_active_seconds']==6
    assert result['timing']['time_improvement'] is None


def test_no_truth_is_pending_with_null_rates_not_success():
    package,annotations,predictions=metric_fixture();annotations['rows']=[]
    result=score(package,annotations,predictions)
    assert result['state']=='pending_human_review' and result['unlabelled']==6
    assert result['decisive']['false_positive_rate'] is None
    assert result['decisive']['false_negative_rate'] is None
    assert result['timing']['total_active_seconds'] is None


@pytest.mark.parametrize('damage',['duplicate','unknown','hash','prediction','sample','bounds','conflict',
    'bool_time','nan_time','zero_time','human','protocol','label'])
def test_invalid_or_unbound_labels_rejected(damage):
    package,annotations,predictions=metric_fixture()
    row=annotations['rows'][0]
    if damage=='duplicate':annotations['rows'].append(copy.deepcopy(row))
    if damage=='unknown':row['sample_id']='missing'
    if damage=='hash':annotations['package_sha256']='wrong'
    if damage=='prediction':predictions['regions'][0]['status']='no_detected_clip'
    if damage=='sample':
        package['samples'][0]['text']='changed'
        annotations['package_sha256']=predictions['package_sha256']=sha256_json(package)
    if damage=='bounds':row['truth_bounds'][0]=-1
    if damage=='conflict':row['label']='complete'
    if damage=='bool_time':row['active_review_ms']=True
    if damage=='nan_time':row['active_review_ms']=float('nan')
    if damage=='zero_time':row['active_review_ms']=0
    if damage=='human':annotations['declared_human_blind_review']=False
    if damage=='protocol':annotations['timing_protocol']='wall_clock'
    if damage=='label':row['label']='passed'
    with pytest.raises(ValueError,match='BENCHMARK_'):score(package,annotations,predictions)


def test_unjudgeable_and_wrong_identity_never_enter_binary_denominators():
    package,annotations,predictions=metric_fixture()
    annotations['rows']=annotations['rows'][:2]
    annotations['rows'][0].update(label='unjudgeable',truth_bounds=None)
    annotations['rows'][1].update(label='identity_mismatch',truth_bounds=None)
    result=score(package,annotations,predictions)
    assert result['state']=='partially_reviewed' and result['truth']['unjudgeable']==1
    assert result['truth']['identity_mismatch']==1 and result['decisive']['precision'] is None
    annotations['rows'][0]['truth_bounds']=[1,1,2,2]
    with pytest.raises(ValueError,match='UNJUDGED'):score(package,annotations,predictions)


def source_fixture(tmp_path):
    reference=tmp_path/'ref.png';image=Image.new('RGB',(240,160),'white')
    ImageDraw.Draw(image).line((55,80,90,80),fill='black',width=3);image.save(reference)
    record={'reference_sha256':sha256_file(reference),'image_size':[240,160],
        'result':{'targets':[{'targetId':'</script><script>bad()</script>','status':'located','container_box':None,
        'part_regions':[{'partId':'title','regions':[{'text':'<unsafe>','box':{'xPx':60,'yPx':50,'widthPx':120,'heightPx':60}}]}]}]}}
    path=tmp_path/'record.json';path.write_text(json.dumps(record),encoding='utf-8')
    return reference,path


def test_preparation_is_blind_sealed_deduplicated_and_keeps_source_files(tmp_path):
    reference,record=source_fixture(tmp_path)
    original=(reference.read_bytes(),record.read_bytes())
    out=tmp_path/'package'
    receipt=prepare([('trial-0',reference,record),('trial-1',reference,record)],out)
    html=(out/'blind-review.html').read_text(encoding='utf-8')
    assert receipt['samples']==2 and receipt['unique_reference_images']==1
    assert 'possible_clip' not in html and 'no_detected_clip' not in html and 'connected_ink' not in html
    assert html.count('data:image/png;base64,')==1
    assert '<script>bad()</script>' not in html and '&lt;unsafe&gt;' in html
    assert (reference.read_bytes(),record.read_bytes())==original
    template=json.loads((out/'annotations-template.json').read_text(encoding='utf-8'))
    package=json.loads((out/'package.json').read_text(encoding='utf-8'))
    predictions=json.loads((out/'predictions.json').read_text(encoding='utf-8'))
    assert template['rows']==[] and not template['declared_human_blind_review']
    assert score(package,template,predictions)['state']=='pending_human_review'
    with pytest.raises(ValueError,match='OUTPUT_MUST_BE_NEW'):prepare([('new',reference,record)],out)


@pytest.mark.parametrize('damage',['image','size','diagnostic','duplicate_case'])
def test_preparation_rejects_inconsistent_cases_without_outputs(tmp_path,damage):
    reference,path=source_fixture(tmp_path)
    record=json.loads(path.read_text(encoding='utf-8'))
    if damage=='image':Image.new('RGB',(240,160),'black').save(reference)
    if damage=='size':record['image_size']=[1,1]
    if damage=='diagnostic':record['edge_verification']={}
    path.write_text(json.dumps(record),encoding='utf-8')
    cases=[('case',reference,path)]*(2 if damage=='duplicate_case' else 1)
    with pytest.raises(ValueError,match='BENCHMARK_'):prepare(cases,tmp_path/'package')
    assert not (tmp_path/'package').exists()


def test_explicit_timer_excludes_blur_and_background_and_exports_only_saved_rows(tmp_path):
    node=shutil.which('node');assert node
    script='''const assert=require('node:assert/strict'),vm=require('node:vm');
const source=require('node:fs').readFileSync(process.argv[1],'utf8');
let now=0,downloaded;
const elements={};for(const id of ['timer','label','notes','left','top','right','bottom','previous','next','editor','progress','start','pause','save','zoom','message','export','reviewer','human','download']){
elements[id]={value:'',checked:false,disabled:false,hidden:false,addEventListener(e,fn){this[e]=fn;}};}
elements.download.click=()=>{};
const cards=[{hidden:true},{hidden:true}];
const document={hidden:false,hasFocus:()=>true,getElementById:id=>elements[id],querySelectorAll:s=>s==='article'?cards:[],addEventListener(e,fn){this[e]=fn;}};
const window={addEventListener(e,fn){this[e]=fn;}};
const REVIEW_DATA={package_sha256:'hash',samples:[{sample_id:'a',image_size:[100,60],proposed_bounds:[20,20,80,40]},
{sample_id:'b',image_size:[100,60],proposed_bounds:[20,20,80,40]}]};
const context={document,window,REVIEW_DATA,performance:{now:()=>now},
Blob:class{constructor(parts){this.parts=parts;}},URL:{createObjectURL:blob=>{downloaded=JSON.parse(blob.parts[0]);return 'blob:test';},revokeObjectURL(){}}};
vm.runInNewContext(source,context);
const svg={dataset:{originX:'50',originY:'40',width:'100',height:'60'},getBoundingClientRect:()=>({left:100,top:200,width:200,height:120})};
assert.deepEqual(Array.from(context.originalPoint(svg,{clientX:120,clientY:220})),[60,50]);
assert.deepEqual(Array.from(context.originalPoint(svg,{clientX:500,clientY:500})),[150,100]);
assert.equal(elements.label.value,'');assert.equal(cards[0].hidden,false);
elements.start.click();now=1000;window.blur();now=100000;
elements.label.value='complete';['left','top','right','bottom'].forEach((id,i)=>elements[id].value=String([21,21,79,39][i]));elements.save.click();
assert.equal(elements.label.value,'');assert.equal(cards[1].hidden,false);
elements.start.click();now=103000;document.hidden=true;document.visibilitychange();
now=203000;document.hidden=false;document.visibilitychange();
elements.start.click();now=204500;elements.label.value='unjudgeable';elements.save.click();
elements.export.click();assert.equal(downloaded,undefined);
elements.reviewer.value='synthetic-test-only';elements.human.checked=true;elements.export.click();
assert.equal(downloaded.rows.length,2);assert.equal(downloaded.rows[0].active_review_ms,1000);
assert.equal(downloaded.rows[1].active_review_ms,4500);assert.equal(downloaded.rows[1].truth_bounds,null);
assert.equal(downloaded.declared_human_blind_review,true);console.log('timer passed');'''
    completed=subprocess.run([node,'-e',script,str(LABELER)],capture_output=True,text=True,timeout=10)
    assert completed.returncode==0,completed.stderr
