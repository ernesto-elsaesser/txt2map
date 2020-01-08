from evaluation import TestsImporter, CorpusAnnotator, SpacyPipeline, SpacyT2MPipeline, CorpusEvaluator

importer = TestsImporter()
annotator = CorpusAnnotator('Tests')
evaluator = CorpusEvaluator('Tests', False, 1)

#importer.import_documents()

#spacy = SpacyPipeline(use_server=True)
#annotator.annotate_all(spacy)

spacy_txt2map = SpacyT2MPipeline()
annotator.annotate_all(spacy_txt2map)

evaluator.evaluate_all(spacy_txt2map.id_)
