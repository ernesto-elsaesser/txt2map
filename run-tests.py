from evaluation import *

importer = TestsImporter()
annotator = CorpusAnnotator('Tests')
evaluator = CorpusEvaluator('Tests', True)

spacy = SpacyPipeline(use_server=True)
gcnl = GCNLPipeline()
cogcomp = CogCompPipeline()
spacy_geo = SpacyT2MPipeline()

#importer.import_documents()
#annotator.annotate_all(spacy)
#annotator.annotate_all(gcnl)
#annotator.annotate_all(spacy_geo)
#annotator.annotate_one(spacy_geo, 'local_way')
annotator.annotate_all(cogcomp)
#evaluator.evaluate_all(spacy_geo.id_)
#evaluator.evaluate_all(gcnl.id_)
