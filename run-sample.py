import logging
from geoparser import Geoparser

logging.basicConfig(format='%(asctime)s %(message)s',
                    level=logging.INFO,
                    datefmt="%H:%M:%S")

sample_text = 'The rapper Jay-Z loves his hometown New York. He grew up in Brooklyn, but now lives in Tribeca and can be seen driving expensive cars down Broadway and 8th Street. His old apartment was located on Flatbush Ave in Bed-Stuy, right next to a McDonald\'s where he used to spend his time. In his song "Empire State of Mind" he mentions the Statue of Liberty, the Empire State Building and the World Trade Center.'

parser = Geoparser()
_ = parser.parse(sample_text)

