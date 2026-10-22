"""Research suggestion, always reviewed; does not alter a signed source claim."""
import os
from functools import lru_cache
from pathlib import Path
from .ml import TextClassifier

@lru_cache(maxsize=4)
def classifier(path):
 return TextClassifier(path) if Path(path).exists() else None

def rule_priority(text):
 text=text.lower()
 # Deliberately simple comparison baseline; negation errors are measured, not hidden.
 if any(w in text for w in ['cuốn trôi','bất tỉnh','không thở','đuối nước','vùi lấp','chảy máu','mắc kẹt','khó thở','co giật','ngừng thở']):return 1
 if any(w in text for w in ['thuốc','sơ tán','hết','thiếu','thực phẩm','nước sạch','bị thương']):return 2
 return 3

def suggest(body):
 path=os.getenv('TRIAGE_MODEL',str(Path(__file__).resolve().parents[2]/'ai/artifacts/triage_model.json'))
 model=classifier(path)
 reasons=[]
 if model:
  pred=model.predict(body.text);confidence=pred['confidence']
  low=not pred['has_known_features'] or confidence<model.model['review_threshold']
  candidate=2 if low else pred['priority']
  reasons.append('Mô hình TF-IDF + Logistic Regression được huấn luyện bằng bộ dữ liệu diễn tập tổng hợp.')
  if low:reasons.append('Nội dung chưa đủ chắc chắn; đưa vào hàng chờ xác minh, không tự gán mức thấp nhất.')
  version=model.model['version']
 else:
  pred={'priority':rule_priority(body.text)};candidate=pred['priority'];confidence=None;low=True;version='rules-v0.2-no-model'
  reasons.append('Chưa tải được mô hình; dùng baseline từ khóa.')
 if rule_priority(body.text)==1:
  candidate=min(candidate,1);reasons.append('Từ khóa nguy hiểm: ưu tiên người trực kiểm tra, kể cả câu phủ định.')
 if 'medical' in body.needs: candidate=min(candidate,1);reasons.append('Người gửi chọn nhu cầu y tế; cần xác minh.')
 if 'evacuation' in body.needs:candidate=min(candidate,2)
 priority=min(body.priority,candidate)
 return {'model_version':version,'suggested_priority':priority,'text_priority':pred['priority'],'requires_review':True,'low_confidence':low,'reasons':reasons,'confidence':confidence,'confidence_kind':'uncalibrated_model_score' if confidence is not None else None}
