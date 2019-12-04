from geoparser import Geoparser
from .evaluator import CorpusEvaluator


class TestEvaluator:

  def __init__(self):
    parser = Geoparser(nlp_model=0)
    self.eval = CorpusEvaluator(parser, 1)
    self.eval.start_corpus('Tests')

  def test_all(self):
    self.test_global_default_sense()
    self.test_global_onto_distance()
    self.test_global_onto_distance_hard()
    self.test_global_top_defaults()
    self.test_global_special_chars()
    self.test_local_node()
    self.test_local_way()
    self.test_local_relation()
    self.test_local_abbrevs()
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

  def test_global_onto_distance_hard(self):
    text = 'The University in San Marcos in California is one of many in America.'
    self.eval.start_document('Global - Ontological Distance Hard', text)
    self.eval.verify_annotation(18, 'San Marcos', 33.14337, -117.16614)
    self.eval.verify_annotation(32, 'California', 37.25022, -119.75126)
    self.eval.verify_annotation(61, 'America', 39.76, -98.5)

  def test_global_top_defaults(self):
    text = '''France is in Europe and California in the United States. 
              Africa is a continent and Mexico and Uruguay are countries.'''
    self.eval.start_document('Global - Fixed Top-Level Senses', text)
    self.eval.verify_annotation(0, 'France', 46, 2)
    self.eval.verify_annotation(13, 'Europe', 48.69096, 9.14062)
    self.eval.verify_annotation(24, 'California', 37.25022, -119.75126)
    self.eval.verify_annotation(42, 'United States', 39.76, -98.5)
    self.eval.verify_annotation(72, 'Africa', 7.1881, 21.09375)
    self.eval.verify_annotation(98, 'Mexico', 23, -102)
    self.eval.verify_annotation(109, 'Uruguay', -33, -56)

  def test_global_special_chars(self):
    text = 'The Mall of Asia in Paranaque City.'
    self.eval.start_document('Global - Special Characters', text)
    self.eval.verify_annotation(4, 'Mall of Asia', 14.5349995, 120.9832017)
    self.eval.verify_annotation(20, 'Parañaque City', 14.48156, 121.01749)

  def test_local_node(self):
    text = 'We met at Checkpoint Charlie in Berlin.'
    self.eval.start_document('Local - OSM Node', text)
    self.eval.verify_annotation(
        10, 'Checkpoint Charlie', 52.5075075, 13.3903737)

  def test_local_way(self):
    text = 'When in Los Angeles check out Hollywood Blvd.'
    self.eval.start_document('Local - OSM Way', text)
    self.eval.verify_annotation(
        30, 'Hollywood Blvd', 34.101596, -118.338724)

  def test_local_relation(self):
    text = 'The Statue of Liberty is in New York.'
    self.eval.start_document('Local - OSM Relation', text)
    self.eval.verify_annotation(4, 'Statue of Liberty', 40.689167, -74.044444)

  def test_local_abbrevs(self):
    text = 'He painted St. Peter\'s Basilica in Rome.'
    self.eval.start_document('Local - Abbreviations', text)
    self.eval.verify_annotation(11, 'St. Peter\'s Basilica', 41.90216, 12.4536)
    self.eval.verify_annotation(35, 'Rome', 41.89193, 12.51133)
