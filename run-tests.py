from evaluation import *

corpus = Corpus('Tests')

spacy = SpacyAnnotator(use_server=False)
gcnl = GCNLAnnotator()
cogcomp = CogCompAnnotator()
t2m = T2MAnnotator('spacy')

res_eval = Evaluator()

corpus.annotate_all(spacy)
#corpus.annotate_all(cogcomp)
#corpus.annotate_all(gcnl)
corpus.annotate_all(t2m)

#corpus.annotate_one(spacy, 'ancestors')

corpus.evaluate_all(t2m, res_eval)
