"""Reproducible group-disjoint training; JSON-only runtime artifact."""
import argparse,csv,hashlib,json,sys
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
BASE=Path(__file__).resolve().parent

def train(data,out):
 rows=list(csv.DictReader(data.open(encoding='utf-8')))
 if len(rows)<30: raise ValueError('Cần ít nhất 30 mẫu và nhiều group độc lập')
 groups={}
 for r in rows:
  label=int(r['priority'])
  if label not in (1,2,3) or not r['text'].strip() or not r['group_id'].strip(): raise ValueError('CSV không hợp lệ')
  previous=groups.setdefault(r['group_id'],label)
  if previous!=label: raise ValueError('Một group có nhãn mâu thuẫn')
 names=sorted(groups)
 train_g,hold_g=train_test_split(names,test_size=.4,stratify=[groups[g] for g in names],random_state=42)
 val_g,test_g=train_test_split(hold_g,test_size=.5,stratify=[groups[g] for g in hold_g],random_state=42)
 assert not(set(train_g)&set(val_g) or set(train_g)&set(test_g) or set(val_g)&set(test_g))
 partitions={k:[r for r in rows if r['group_id'] in set(g)] for k,g in [('train',train_g),('validation',val_g),('test',test_g)]}
 vec=TfidfVectorizer(strip_accents='unicode',ngram_range=(1,2),sublinear_tf=True)
 x=vec.fit_transform([r['text'] for r in partitions['train']]);y=[int(r['priority']) for r in partitions['train']]
 clf=LogisticRegression(class_weight='balanced',C=4,max_iter=1000,random_state=42).fit(x,y)
 report={'dataset_sha256':hashlib.sha256(data.read_bytes()).hexdigest(),'source':'See CSV source column; bundled data are synthetic, NOT field data','seed':42,'group_split':{'train':train_g,'validation':val_g,'test':test_g},'samples':{k:len(v) for k,v in partitions.items()},'metrics':{}}
 for k in ['validation','test']:
  samples=partitions[k]; actual=[int(r['priority']) for r in samples];pred=clf.predict(vec.transform([r['text'] for r in samples]))
  sys.path.insert(0,str(BASE.parent/'backend'))
  from app.triage import rule_priority
  baseline=[rule_priority(r['text']) for r in samples]
  report['metrics'][k]={'rules_baseline':classification_report(actual,baseline,labels=[1,2,3],output_dict=True,zero_division=0),'classification_report':classification_report(actual,pred,labels=[1,2,3],output_dict=True,zero_division=0),'confusion_matrix':confusion_matrix(actual,pred,labels=[1,2,3]).tolist()}
 artifact={'version':'tfidf-logreg-demo-v0.2','training_source':report['source'],'dataset_sha256':report['dataset_sha256'],'vocabulary':vec.vocabulary_,'idf':vec.idf_.tolist(),'coef':clf.coef_.tolist(),'intercept':clf.intercept_.tolist(),'classes':clf.classes_.tolist(),'review_threshold':.60}
 out.mkdir(parents=True,exist_ok=True)
 # numpy integer indices need explicit conversion
 artifact['vocabulary']={k:int(v) for k,v in artifact['vocabulary'].items()}
 (out/'triage_model.json').write_text(json.dumps(artifact,ensure_ascii=False),encoding='utf-8')
 (out/'evaluation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 sys.path.insert(0,str(BASE.parent/'backend'))
 from app.ml import TextClassifier
 runtime=TextClassifier(out/'triage_model.json')
 for r in rows:
  probs=clf.predict_proba(vec.transform([r['text']]))[0]
  got=runtime.predict(r['text'])
  assert np.allclose(probs,got['scores'],atol=1e-9), 'Export differs from sklearn'
 print(json.dumps({'samples':report['samples'],'synthetic_test_macro_f1':report['metrics']['test']['classification_report']['macro avg']['f1-score'],'runtime_parity_samples':len(rows)},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=BASE/'data/sos_demo.csv');p.add_argument('--out',type=Path,default=BASE/'artifacts');a=p.parse_args();train(a.data,a.out)
