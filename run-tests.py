from evaluation import *

annotator = CorpusAnnotator('Tests')
evaluator = CorpusEvaluator('Tests', True)

spacy = SpacyPipeline(use_server=True)
gcnl = GCNLPipeline()
cogcomp = CogCompPipeline()
spacy_geo = SpacyT2MPipeline()
cogcomp_geo = CogCompT2MPipeline()

#annotator.annotate_all(spacy)
#annotator.annotate_all(gcnl)
#annotator.annotate_all(spacy_geo)
#annotator.annotate_all(cogcomp)
#annotator.annotate_all(cogcomp_geo)

annotator.annotate_one(cogcomp_geo, 'global_onto_sim')

#evaluator.evaluate_all(spacy_geo.id_)
#evaluator.evaluate_all(gcnl.id_)
evaluator.evaluate_all(cogcomp_geo.id_)
