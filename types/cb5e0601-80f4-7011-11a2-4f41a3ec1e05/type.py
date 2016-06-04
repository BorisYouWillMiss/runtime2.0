
import re


class VDOM_growl(VDOM_object):

  def render(self, contents=""):

    vstyle = u''
    style = int(self.style)
    if style > 0:
      x = style
      if x > 3: x = 3
      if x > 1:
        xa = {
          1: 'yellow information',
          2: 'yellow warning',
          3: 'red error'
        }
        vstyle = xa[x]
    else:
      if self.userclass != "":
        vstyle = unicode(self.userclass).replace('"', '&quot;')

    res = u''
    if self.active == '1':
      title = unicode(self.title).strip().replace('"', '&quot;')
      text = unicode(self.text).strip().replace('"', '&quot;')
      if title != '' and text != '':
        res += "<span class='growls' style='display:none' vstyle='%s'><span>%s</span><div>%s</div></span>" % ( vstyle, title, text )

    return res

  def wysiwyg(self, contents=""):
    from scripting.utils.wysiwyg import get_empty_wysiwyg_value

    self.zindex = "0"
    self.width = "50"
    self.height = "50"

    image_id = "325920db-4f3a-da8e-bbfe-16b3a511efbe"
    result = get_empty_wysiwyg_value(self, image_id, 0.4)

    return VDOM_object.wysiwyg(self, contents=result)
