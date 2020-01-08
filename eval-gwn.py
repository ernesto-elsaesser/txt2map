from geoparser import Config
from evaluation import GeoWebNewsImporter, CorpusAnnotator, SpacyPipeline, GCNLPipeline, GCNLT2MPipeline, SpacyT2MPipeline, CorpusEvaluator

importer = GeoWebNewsImporter()
annotator = CorpusAnnotator('GeoWebNews')
evaluator = CorpusEvaluator('GeoWebNews', True, 161)

ner = SpacyPipeline(use_server=True)
geoparse = SpacyT2MPipeline()

#importer.import_documents()
#annotator.annotate_all(ner)
#annotator.annotate_all(geoparse)
evaluator.evaluate_all(geoparse.id_)
