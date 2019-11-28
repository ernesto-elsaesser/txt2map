from .evaluator import CorpusEvaluator


class TestEvaluator:

  def __init__(self):
    self.eval = CorpusEvaluator(1)
    self.eval.start_corpus('Tests')

  def test_all(self):
    self.test_geoname()
    self.test_geoname_disambiguation()
    self.test_osm_point()
    self.test_osm_polygon()
    report = self.eval.evaluation_report()
    print(report)

  def test_geoname(self):
    text = 'I love Paris.'
    self.eval.start_document('GeoNamesRecognition', text)
    self.eval.verify_annotation(7, 'Paris', 48.85341, 2.3488)

  def test_geoname_disambiguation(self):
    text = 'I love Paris in Lamar County, Texas.'
    self.eval.start_document('GeoNamesResolution', text)
    self.eval.verify_annotation(7, 'Paris', 33.66094, -95.55551)

  def test_osm_point(self):
    text = 'We met at Checkpoint Charlie in Berlin.'
    self.eval.start_document('OSMPointMatch', text)
    self.eval.verify_annotation(10, 'Checkpoint Charlie', 52.5075075, 13.3903737)

  def test_osm_polygon(self):
    text = 'The Statue of Liberty is in New York.'
    self.eval.start_document('OSMPolygonMatch', text)
    self.eval.verify_annotation(4, 'Statue of Liberty', 40.689167, -74.044444)
