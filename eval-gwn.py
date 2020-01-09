from evaluation import *

corpus = Corpus('GeoWebNews')

spacy = SpacyAnnotator(use_server=True)
gcnl = GCNLAnnotator()
cogcomp = CogCompAnnotator()
gaz = GazetteerAnnotator('cogcomp')
t2m = T2MAnnotator('spacy')

rec_eval = Evaluator(tolerance_global=161, tolerance_local=161, resol=False)
res_eval = Evaluator(tolerance_global=161, tolerance_local=161)

#corpus.annotate_all(spacy)
corpus.annotate_all(gaz)
#corpus.annotate_all(cogcomp)

#corpus.annotate_one(cogcomp, '0')

#corpus.annotate_all(gcnl)
#corpus.annotate_all(t2m)

corpus.evaluate_all(gaz, rec_eval)
