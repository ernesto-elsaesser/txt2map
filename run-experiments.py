from evaluation import *

# annotators
spacy = SpacyAnnotator(port=8001)
gcnl = GCNLAnnotator()
cogcomp = CogCompAnnotator(port=8002)
spacy_gaz = GazetteerAnnotator('spacy')
cogcomp_gaz = GazetteerAnnotator('cogcomp')
spacy_t2m = T2MAnnotator('spacy')
cogcomp_t2m = T2MAnnotator('cogcomp')

# corpora
tests = Corpus('Tests')
gwn = Corpus('GeoWebNews')

# evaluators
ev_rec_161 = Evaluator(tolerance_local=161, resol=False)
ev_res_161 = Evaluator(tolerance_local=161)
ev_rec = Evaluator(resol=False)
ev_res = Evaluator()

#gwn.annotate_all(spacy)
#gwn.annotate_all(spacy_gaz)
gwn.evaluate_all(spacy_gaz, ev_rec)

'''
tests.annotate_all(spacy)
tests.annotate_all(spacy_gaz)
tests.annotate_all(spacy_t2m)
tests.evaluate_all(spacy_t2m, ev_rec)
'''
