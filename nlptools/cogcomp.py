
class CogCompNLP:

  @staticmethod
  def import_annotations(doc, cc_text):
    text = doc.text()
    l = len(text)
    cc_l = len(cc_text)
    i = pos = 0
    ent_pos = ent_group = ent_phrase = None

    while pos < l and i < cc_l:
      c = cc_text[i]
      if c == '[':
        ent_pos = pos
        ent_phrase = ''
        if cc_text[i+1] == 'M':
          ent_group = 'msc'
          i += 6
        else:
          ent_group = cc_text[i+1:i+4].lower()
          i += 5
      elif c == ']':
        if ent_phrase.startswith('The ') or ent_phrase.startswith('the '):
          ent_phrase = ent_phrase[4:]
          ent_pos += 4
        doc.annotate('ner', ent_pos, ent_phrase, ent_group, 'cogcomp_conll')
        ent_pos = ent_group = ent_phrase = None
        i += 1
      else:
        if c == text[pos]:
          if ent_phrase != None:
            ent_phrase += c
          pos += 1
        i += 1
