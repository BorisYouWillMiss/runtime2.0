# coding=utf8

from scripting import server, application, log, session, request, response, VDOM_object, obsolete_request




class VDOM_richtext(VDOM_object):

    def render(self, contents=""):
        if self.visible == "1":
            invisible = ""
        else:
            invisible = "display:none;"

        if self.classname == "":
            classname = ""
        else:
            classname = " class='%s' " % ( self.classname )

        if self.overflow == "1":
            overflow = u"hidden"
        elif self.overflow == "2":
            overflow = u"scroll"
        elif self.overflow == "3":
            overflow = u"visible"
        else:
            overflow = u"auto"

        style = u"z-index:%s;position:%s;top:%spx;left:%spx;width:%spx;%s" % (self.zindex, self.position, self.top, self.left, self.width, invisible)
        styles = {"text-align" : "", "font" : "", "color" : "", "text-decoration" : "", "height" : "", "overflow" : overflow}
        if "" != self.align:
            styles["text-align"] = "%s" % self.align
        if "" != self.color:
            styles["color"] = "#%s" % self.color
        if "" != self.font:
            styles["font"] = "%s" % self.font.replace('"', "'")
        if "1" == self.underlined:
            styles["text-decoration"] += "underline"
        if "1" == self.strikethrough:
            styles["text-decoration"] += "line-through"
        #if "" != self.height and "0" != self.height:
        #   styles["height"] = " %spx; " % self.height
        #   styles["overflow"] = " auto; "
        #if "" != self.height:
        #   styles["height"] = "%spx" % self.height
        if "" != self.height and "0" != self.height:
            styles["height"] = "%spx" % self.height

        for key in styles:
            if "" != styles[key]:
                style += (key + ":" + styles[key]) + ';'

        the_value = self.value
        #if "" == the_value:
        #  the_value = "Text"

        id = 'o_' + (self.id).replace('-', '_')

        if VDOM_CONFIG_1["DEBUG"] == "1":
            debug_info = u"objtype='richtext' objname='%s' ver='%s'" % (self.name, self.type.version)
        else:
            debug_info = u""

        result = u"<div %s id=\"%s\" style=\"%s\" %s>%s</div>" % (debug_info, id, style, classname, the_value)

        return VDOM_object.render(self, contents=result)

    def wysiwyg(self, contents=""):
        the_value = self.value

        empty_value = \
            u"""<svg>
                <text fill="#cccccc" x="7" y="13" >Text</text>
            </svg>
            """ if the_value == "" else ""

        color = """color="%s" """ % self.color if self.color != "" else ""

        cdata = "<![CDATA"+"["+the_value+"]"+"]>"

        result = \
            u"""<container id="{id}" visible="{visible}" zindex="{zindex}" hierarchy="{hierarchy}" order="{order}" top="{top}" left="{left}" width="{width}" height="{height}">
                    {empty_value}
                    <htmltext top="{textTop}" left="{textLeft}" width="{width}" height="{height}" {color} editable="{value}">{cdata}</htmltext>
                    {contents}
                </container>""".format(
                    id = self.id,
                    visible = self.visible,
                    zindex = self.zindex,
                    hierarchy = self.hierarchy,
                    order = self.order,
                    top = self.top,
                    left = self.left,
                    width = self.width,
                    height = self.height,
                    empty_value = empty_value,
                    textTop = 0,
                    textLeft = 0,
                    color = color,
                    value = "value",
                    cdata = cdata,
                    contents = contents
                )

        return VDOM_object.wysiwyg(self, contents=result)

    
