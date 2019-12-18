from geoparser import Geoparser
from .evaluator import Annotation, CorpusEvaluator


class TestEvaluator:

  def __init__(self):
    parser = Geoparser(use_large_model=False)
    self.eval = CorpusEvaluator(parser)

  def test_all(self):
    self.test_global_default_sense()
    self.test_global_onto_sim()
    self.test_global_onto_sim_hard()
    self.test_global_top_defaults()
    self.test_global_name_sim()
    self.test_global_demonyms()
    self.test_global_two()
    self.test_embedded()
    self.test_ancestors()
    self.test_local_node()
    self.test_local_way()
    self.test_local_relation()
    self.test_local_abbrevs()
    self.test_local_abbrevs_2()
    self.test_local_special_chars()
    self.test_local_fuzzy()

    summary = self.eval.corpus_summary(1)
    print('Total:', summary)

  def test_global_default_sense(self):
    text = 'I love Paris.'
    anns = [('Paris', 0, 0, 2988507)]
    self._test(False, 'Default Sense', text, anns)

  def test_global_onto_sim(self):
    text = 'I love Paris in Lamar County, Texas.'
    anns = [('Paris', 0, 0, 4717560)]
    anns = [('Lamar County', 0, 0, 4705086)]
    anns = [('Texas', 0, 0, 4736286)]
    self._test(False, 'Ontological Similarity', text, anns)

  def test_global_onto_sim_hard(self):
    text = 'The University in San Marcos in California is one of many in America.'
    anns = [('San Marcos', 0, 0, 5392368),
            ('California', 0, 0, 5332921),
            ('America', 0, 0, 6252001)]
    self._test(False, 'Ontological Similarity Hard', text, anns)

  def test_global_top_defaults(self):
    text = '''France is in Europe and California in the United States. 
              Africa is a continent and Mexico and Uruguay are countries.'''
    anns = [('France', 0, 0, 3017382),
            ('Europe', 0, 0, 6255148),
            ('California', 0, 0, 5332921),
            ('United States', 0, 0, 6252001),
            ('Africa', 0, 0, 6255146),
            ('Mexico', 0, 0, 3996063),
            ('Uruguay', 0, 0, 3439705)]
    self._test(False, 'Fixed Top-Level Senses', text, anns)

  def test_global_name_sim(self):
    text = 'Where is Fire Island?'
    anns = [('Fire Island', 0, 0, 5117145)]
    self._test(False, 'Prefer Similar Names', text, anns)

  def test_global_demonyms(self):
    text = 'Che Guevara is burried in the Cuban city of Santa Clara.'
    anns = [('Santa Clara', 0, 0, 3537906)]
    self._test(False, 'Demonyms', text, anns)

  def test_global_two(self):
    text = 'Paris in in France and Los Angeles in California.'
    anns = [('Paris', 0, 0, 2988507), ('France', 0, 0, 3017382),
            ('Los Angeles', 0, 0, 5368361), ('California', 0, 0, 5332921)]
    self._test(False, 'Two Clusters', text, anns)

  def test_ancestors(self):
    text = 'Avoyelles task force arrests 14. They live in Cottonport, US.'
    anns = [('Avoyelles', 0, 0, 4315243), ('Cottonport', 0, 0, 4320874)]
    self._test(False, 'Find Ancestors', text, anns)

  def test_embedded(self):
    text = 'He is from South Africa.'
    anns = [('South Africa', 0, 0, 953987)]
    self._test(False, 'Embedded Names', text, anns)

  def test_local_node(self):
    text = 'We met at Checkpoint Charlie in Berlin.'
    anns = [('Checkpoint Charlie', 52.5075075, 13.3903737, None)]
    self._test(True, 'OSM Node', text, anns)

  def test_local_way(self):
    text = 'When in Los Angeles check out Hollywood Blvd.'
    anns = [('Los Angeles', 0, 0, 5368361),
            ('Hollywood Blvd', 34.101596, -118.338724, None)]
    self._test(True, 'OSM Way', text, anns)

  def test_local_relation(self):
    text = 'The Statue of Liberty is in New York.'
    anns = [('Statue of Liberty', 40.689167, -74.044444, None)]
    self._test(True, 'OSM Relation', text, anns)

  def test_local_abbrevs(self):
    text = 'He painted St. Peter\'s Basilica in Rome.'
    anns = [('St. Peter\'s Basilica', 41.90216, 12.4536, None)]
    self._test(True, 'Abbreviations', text, anns)

  def test_local_abbrevs_2(self):
    text = 'On N. Bedford Drive in Beverly Hills.'
    anns = [('N. Bedford Drive', 34.0678280, -118.4049976, None)]
    self._test(True, 'Abbreviations 2', text, anns)

  def test_local_special_chars(self):
    text = 'The Mall of Asia in Paranaque City.'
    anns = [('Mall of Asia', 14.5349995, 120.9832017, None)]
    self._test(True, 'Special Characters', text, anns)

  def test_local_fuzzy(self):
    # in the OSM data Caesars is written without apostrophe
    text = 'She sang at Caesar\'s Palace in Las Vegas.'
    anns = [('Caesar\'s Palace', 36.11672, -115.17518, None)]
    self._test(True, 'Fuzzy Matching', text, anns)

  def _test(self, is_local, title, text, annotations):
    prefix = 'Local' if is_local else 'Global'
    document = prefix + ' - ' + title
    self.eval.start_document(document, text)
    for name, lat, lon, geoname_id in annotations:
      pos = text.find(name)
      annotation = Annotation(pos, name, lat, lon, geoname_id)
      self.eval.verify_annotation(annotation)
    summary = self.eval.document_summary(1)
    print(summary)

