from planner import Planner
import json

p = Planner('qwen2.5-1.5b-instruct-q4_k_m.gguf')
r = p.planifier('ouvre vlc')
print('ACTION:', r.get('action'))
print('Parametres:', json.dumps(
    r.get('parametres', {}), ensure_ascii=False, indent=2))
