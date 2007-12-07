
from buildbot.status.web.base import ICurrentBox, HtmlResource, Box, map_branches, build_get_class

from nevow import tags
from nevow.url import URL
from nevow.flat import flatten

# /one_box_per_builder
#  accepts builder=, branch=
class TenBoxesPerBuilder(HtmlResource):
    """This shows a narrow table with one row per build. The leftmost column
    contains the builder name. The next column contains the results of the
    most recent build. The right-hand column shows the builder's current
    activity.

    builder=: show only builds for this builder. Multiple builder= arguments
              can be used to see builds from any builder in the set.
    """

    title = "Latest Build"

    def body(self, req):
        status = self.getStatus(req)
        
        builders = req.args.get("builder", status.getBuilderNames())
        branches = [b for b in req.args.get("branch", []) if b]

        tag = tags.div()
        tag[tags.h2["Latest builds: ", ", ".join(branches)]]

        table = tags.table()
        tag[table]

        for bn in builders:
            builder = status.getBuilder(bn)
            row = tags.tr()
            table[row]
            row[tags.td(class_="box")[bn]]

            current_box = ICurrentBox(builder).getBox(status)
            row[tags.xml(current_box.td(align="center"))]

            builds = list(builder.generateFinishedBuilds(map_branches(branches),
                                                         num_builds=10))
            if builds:
                for b in builds:
                    url = URL.fromString(self.path_to_root(req) or "./")
                    url = url.child("builders")
                    url = url.child(bn)
                    url = url.child("builds")
                    url = url.child(b.getNumber())
                    try:
                        label = b.getProperty("got_revision")
                    except KeyError:
                        label = None
                    if not label or len(str(label)) > 20:
                        label = "#%d" % b.getNumber()
                    label = [flatten(tags.a(href=url)[label])]
                    label.extend(b.getText())
                    box = Box(label, b.getColor(),
                              class_="LastBuild box %s" % build_get_class(b))
                    row[tags.xml(box.td(align="center"))]
            else:
                row[tags.td(class_="LastBuild box")["no build"]]
        return flatten(tag)
