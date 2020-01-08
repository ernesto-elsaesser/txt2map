from evaluation import TestsImporter, CorpusAnnotator, SpacyPipeline, GCNLPipeline, GCNLT2MPipeline, SpacyT2MPipeline, CorpusEvaluator

importer = TestsImporter()
annotator = CorpusAnnotator('Tests')
evaluator = CorpusEvaluator('Tests', False, 1)

spacy = SpacyPipeline(use_server=True)
spacy_txt2map = SpacyT2MPipeline()

#importer.import_documents()
#annotator.annotate_all(spacy)
annotator.annotate_all(spacy_txt2map)
#annotator.annotate_one(spacy_txt2map, 'local_way')
evaluator.evaluate_all(spacy_txt2map.id_)
