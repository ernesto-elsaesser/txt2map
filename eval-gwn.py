from geoparser import Config
from evaluation import GeoWebNewsImporter, CorpusAnnotator, SpacyPipeline, GCNLPipeline, GCNLT2MPipeline, SpacyT2MPipeline, CorpusEvaluator

importer = GeoWebNewsImporter()
annotator = CorpusAnnotator('GeoWebNews')
evaluator = CorpusEvaluator('GeoWebNews', False, 1)

spacy = SpacyPipeline(use_server=True)
spacy_txt2map = SpacyT2MPipeline()

#importer.import_documents()
annotator.annotate_all(spacy)
#annotator.annotate_all(spacy_txt2map)
#evaluator.evaluate_all(spacy_txt2map.id_)
