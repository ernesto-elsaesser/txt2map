from evaluation import TestsImporter, CorpusAnnotator, SpacyPipeline, GCNLPipeline, GCNLT2MPipeline, SpacyT2MPipeline, CorpusEvaluator

importer = TestsImporter()
annotator = CorpusAnnotator('Tests')
evaluator = CorpusEvaluator('Tests', True, 1)

ner = SpacyPipeline(use_server=True)
geoparse = SpacyT2MPipeline()

#importer.import_documents()
#annotator.annotate_all(ner)
annotator.annotate_all(geoparse)
#annotator.annotate_one(geoparse, 'local_way')
evaluator.evaluate_all(geoparse.id_)
