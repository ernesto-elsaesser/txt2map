from .evaluator import CorpusEvaluator


class TestEvaluator:

  def __init__(self):
    self.eval = CorpusEvaluator(1)
    self.eval.start_corpus('Tests')

  def test_all(self):
    self.test_global_default_sense()
    self.test_global_onto_distance()
    self.test_local_point()
    self.test_local_polygon()
    report = self.eval.corpus_report()
    print(report)

  def test_global_default_sense(self):
    text = 'I love Paris.'
    self.eval.start_document('Global - Default Sense', text)
    self.eval.verify_annotation(7, 'Paris', 48.85341, 2.3488)

  def test_global_onto_distance(self):
    text = 'I love Paris in Lamar County, Texas.'
    self.eval.start_document('Global - Ontological Distance', text)
    self.eval.verify_annotation(7, 'Paris', 33.66094, -95.55551)

  def test_local_point(self):
    text = 'We met at Checkpoint Charlie in Berlin.'
    self.eval.start_document('Local - Point', text)
    self.eval.verify_annotation(10, 'Checkpoint Charlie', 52.5075075, 13.3903737)

  def test_local_polygon(self):
    text = 'The Statue of Liberty is in New York.'
    self.eval.start_document('Local - Polygon', text)
    self.eval.verify_annotation(4, 'Statue of Liberty', 40.689167, -74.044444)
