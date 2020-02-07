import sys
import re
import requests
import html2text
from geoparser import Document, PipelineBuilder

cogcomp_url = sys.argv[1]
page_url = sys.argv[2]
output_path = sys.argv[3]

response = requests.get(url=page_url)
response.encoding = 'utf-8'
html = response.text
h2t = html2text.HTML2Text()
h2t.ignore_links = True
h2t.ignore_tables = True
h2t.ignore_images = True
h2t.ignore_emphasis = True
text = h2t.handle(html)
text = re.sub('#+ +', '', text)

builder = PipelineBuilder()
builder.cogcomp_url = cogcomp_url

pipe = builder.build('cogcomp')
doc = Document(text=text)
pipe.annotate(doc)

json = doc.export_layers()

with open(output_path, 'w') as f:
  f.write(json)