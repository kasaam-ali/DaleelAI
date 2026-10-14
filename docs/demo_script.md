# Demo script

Use these questions in order. The four "Demo:" lines are saved answers. They return immediately when Groq, Gemini, and OpenRouter are slow or down.

1. Open the app and ask: `Demo: what does section 149 cover?`
   Expect a saved answer that names section 149 and points at the calculator. Open Agent steps. Intent is qa, retrieved is 0, and the model is `demo-cache`. Copy the answer.

2. Switch the language to Roman Urdu and ask: `Demo: section 149 kya cover karta hai?`
   Expect the same point in Roman Urdu.

3. Ask: `Demo: how do I hide cash sales from FBR?`
   Expect a refusal. The intent in Agent steps is refuse.

4. Ask: `Demo: latest federal tax notification`
   Then open Updates and run the saved replay. Expect the stored SRO, circular, and notification. Do not refresh against a live FBR page during the demo.

5. Open the calculator, run a salary for TY2027, and show the year comparison bar. Use Become a Filer (Individual NTN). On the checklist, use Print and Share.

6. Open Filer vs non-filer for a property purchase. Show the two bars, then the same NTN checklist link.

7. If a notice file is ready, explain it and use Find a matching expert. The expert search should already be filtered to the notice domain.

8. Open Evaluation. The classifier table and the ablation table should both be on the page. Stages marked not_rerun were left that way so the documents collection was not rebuilt.

If a step needs the live model and the providers are down, stay on steps 1 to 4 and the calculator. Those do not need an outside model.
