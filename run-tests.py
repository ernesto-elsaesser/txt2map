from evaluation import TestsImporter, CorpusAnnotator, SpacyPipeline, GCNLPipeline, GCNLT2MPipeline, SpacyT2MPipeline, CorpusEvaluator

importer = TestsImporter()
annotator = CorpusAnnotator('Tests')
evaluator = CorpusEvaluator('Tests', True, 1)

spacy = SpacyPipeline(use_server=True)
gcnl = GCNLPipeline()
spacy_geo = SpacyT2MPipeline()

#importer.import_documents()
#annotator.annotate_all(spacy)
#annotator.annotate_all(gcnl)
#annotator.annotate_all(spacy_geo)
#annotator.annotate_one(spacy_geo, 'local_way')
#evaluator.evaluate_all(spacy_geo.id_)
evaluator.evaluate_all(gcnl.id_)
