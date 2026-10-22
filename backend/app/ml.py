"""Trusted JSON linear-model inference, no pickle loading and no sklearn at runtime."""
import collections,json,math,re,unicodedata
from pathlib import Path
class TextClassifier:
 def __init__(self,path):
  self.path=Path(path);self.model=json.loads(self.path.read_text(encoding='utf-8'))
 def predict(self,text):
  m=self.model
  clean=''.join(c for c in unicodedata.normalize('NFKD',text.lower()) if not unicodedata.combining(c))
  tokens=re.findall(r'\b\w\w+\b',clean)
  grams=tokens+[' '.join(tokens[i:i+2]) for i in range(len(tokens)-1)]
  counts=collections.Counter(m['vocabulary'][g] for g in grams if g in m['vocabulary'])
  weights={i:(1+math.log(n))*m['idf'][i] for i,n in counts.items()}
  norm=math.sqrt(sum(w*w for w in weights.values()))
  if norm: weights={i:w/norm for i,w in weights.items()}
  logits=[b+sum(row[i]*w for i,w in weights.items()) for row,b in zip(m['coef'],m['intercept'])]
  peak=max(logits);exp=[math.exp(v-peak) for v in logits];scores=[v/sum(exp) for v in exp]
  best=max(range(len(scores)),key=scores.__getitem__)
  return {'priority':m['classes'][best],'confidence':scores[best],'scores':scores,'has_known_features':bool(weights)}
