from llama_cpp import Llama

# Models telecharges

# path = "models/LFM2.5-1.2B-Instruct-BF16.gguf"
# path = "models/Phi-4-mini-instruct-Q4_K_M.gguf"
path = "models/Hermes-3-Llama-3.2-3B-Q8_0.gguf"
# path = "models/Phi-4-mini-instruct.Q8_0.gguf"


llm = Llama(model_path=path, verbose=False)
prompt = "Q: breivly  tell me how to turn off my PC :"
output = llm(prompt, max_tokens=150)
print("✅ Test OK - Réponse :", output['choices'][0]['text'].strip()) # type: ignore
