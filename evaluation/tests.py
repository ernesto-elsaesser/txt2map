from geoparser import Geoparser
from .evaluator import Annotation, CorpusEvaluator


class TestEvaluator:

  def __init__(self):
    parser = Geoparser(nlp_model=0)
    self.eval = CorpusEvaluator(parser)
    self.eval.start_corpus('Tests')

  def test_all(self):
    self.test_global_default_sense()
    self.test_global_onto_sim()
    self.test_global_onto_sim_hard()
    self.test_global_top_defaults()
    self.test_global_special_chars()
    self.test_global_name_sim()
    self.test_local_node()
    self.test_local_way()
    self.test_local_relation()
    self.test_local_abbrevs()
    self.test_local_fuzzy()

    summary = self.eval.corpus_summary(1)
    print('Total:', summary)

  def test_global_default_sense(self):
    text = 'I love Paris.'
    anns = [('Paris', 48.85341, 2.3488)]
    self._test(False, 'Default Sense', text, anns)

  def test_global_onto_sim(self):
    text = 'I love Paris in Lamar County, Texas.'
    anns = [('Paris', 33.66094, -95.55551)]
    self._test(False, 'Ontological Similarity', text, anns)

  def test_global_onto_sim_hard(self):
    text = 'The University in San Marcos in California is one of many in America.'
    anns = [('San Marcos', 33.14337, -117.16614),
            ('California', 37.25022, -119.75126)]
    self._test(False, 'Ontological Similarity Hard', text, anns)

  def test_global_top_defaults(self):
    text = '''France is in Europe and California in the United States. 
              Africa is a continent and Mexico and Uruguay are countries.'''
    anns = [('France', 46, 2),
            ('Europe', 48.69096, 9.14062),
            ('California', 37.25022, -119.75126),
            ('United States', 39.76, -98.5),
            ('Africa', 7.1881, 21.09375),
            ('Mexico', 23, -102),
            ('Uruguay', -33, -56)]
    self._test(False, 'Fixed Top-Level Senses', text, anns)

  def test_global_name_sim(self):
    text = 'Where is Fire Island?'
    anns = [('Fire Island', 40.6476, -73.14595)]
    self._test(False, 'Prefer Similar Names', text, anns)

  def test_global_special_chars(self):
    text = 'The Mall of Asia in Paranaque City.'
    anns = [('Mall of Asia', 14.5349995, 120.9832017)]
    self._test(False, 'Special Characters', text, anns)

  def test_local_node(self):
    text = 'We met at Checkpoint Charlie in Berlin.'
    anns = [('Checkpoint Charlie', 52.5075075, 13.3903737)]
    self._test(True, 'OSM Node', text, anns)

  def test_local_way(self):
    text = 'When in Los Angeles check out Hollywood Blvd.'
    anns = [('Hollywood Blvd', 34.101596, -118.338724)]
    self._test(True, 'OSM Way', text, anns)

  def test_local_relation(self):
    text = 'The Statue of Liberty is in New York.'
    anns = [('Statue of Liberty', 40.689167, -74.044444)]
    self._test(True, 'OSM Relation', text, anns)

  def test_local_abbrevs(self):
    text = 'He painted St. Peter\'s Basilica in Rome.'
    anns = [('St. Peter\'s Basilica', 41.90216, 12.4536)]
    self._test(True, 'Abbreviations', text, anns)

  def test_local_fuzzy(self):
    # in the OSM data Caesars is written without apostrophe
    text = 'She sang at Caesar\'s Palace in Las Vegas.'
    anns = [('Caesar\'s Palace', 36.11672, -115.17518)]
    self._test(True, 'Fuzzy Matching', text, anns)

  def _test(self, is_local, title, text, annotations):
    prefix = 'Local' if is_local else 'Global'
    document = prefix + ' - ' + title
    self.eval.start_document(document, text)
    for name, lat, lng in annotations:
      pos = text.find(name)
      annotation = Annotation(pos, name, lat, lng)
      self.eval.verify_annotation(annotation)
    summary = self.eval.document_summary(1)
    print(summary)

