from buildbot.status.web.base import HtmlResource, map_branches, build_get_class, path_to_builder, path_to_build
from buildbot.status.builder import SUCCESS, WARNINGS, FAILURE, SKIPPED, EXCEPTION, RETRY
from buildbot.status.web.waterfall import WaterfallStatusResource
from buildbot.status import html
from twisted.web.util import Redirect
from twisted.internet import defer

from twisted.web.template import tags, flattenString

_backgroundColors = {
    SUCCESS: "green",
    WARNINGS: "orange",
    FAILURE: "red",
    SKIPPED: "blue",
    EXCEPTION: "purple",
    RETRY: "purple",
    
    # This is a buildbot bug or something.
    None: "yellow",
    }

# /boxes[-things]
#  accepts builder=, branch=, num_builds=
class TenBoxesPerBuilder(HtmlResource):
    """This shows a narrow table with one row per build. The leftmost column
    contains the builder name. The next column contains the results of the
    most recent build. The right-hand column shows the builder's current
    activity.

    builder=: show only builds for this builder. Multiple builder= arguments
              can be used to see builds from any builder in the set.
    """

    title = "Latest Build"

    def __init__(self, categories=None):
        HtmlResource.__init__(self)
        self.categories = categories


    @defer.inlineCallbacks
    def content(self, req, context):
        body = yield self.body(req)
        context['content'] = body
        template = req.site.buildbot_service.templates.get_template("empty.html")
        return template.render(**context)


    def body(self, req):
        status = self.getStatus(req)
        
        builders = req.args.get("builder", status.getBuilderNames(categories=self.categories))
        branches = [b for b in req.args.get("branch", []) if b]
        if branches:
            defaultCount = "1"
        else:
            defaultCount = "10"
        num_builds = int(req.args.get("num_builds", [defaultCount])[0])

        tag = tags.div()
        tag(tags.h2("Latest builds: ", ", ".join(branches)))

        table = tags.table()
        tag(table)

        for bn in builders:
            builder = status.getBuilder(bn)
            state = builder.getState()[0]
            row = tags.tr()
            table(row)
            builderLink = path_to_builder(req, builder)
            row(tags.td(class_="box %s" % (state,))(tags.a(href=builderLink)(bn)))

            # current_box = ICurrentBox(builder).getBox(status)
            # row(tags.xml(current_box.td(align="center")))

            builds = list(builder.generateFinishedBuilds(map_branches(branches),
                                                         num_builds=num_builds))
            if builds:
                for b in builds:
                    url = path_to_build(req, b)
                    try:
                        label = b.getProperty("got_revision")
                    except KeyError:
                        label = None
                    # Label should never be "None", but sometimes
                    # buildbot has disgusting bugs.
                    if not label or label == "None" or len(str(label)) > 20:
                        label = "#%d" % b.getNumber()
                    row(                         tags.td(
                            align="center",
                            bgcolor=_backgroundColors[b.getResults()],
                            class_=("LastBuild box ", build_get_class(b)))([
                                (element, tags.br)
                                for element
                                in [tags.a(href=url)(label)] + b.getText()]) )
            else:
                row(tags.td(class_="LastBuild box")("no build"))
        return flattenString(req, tag)

class TwistedWebStatus(html.WebStatus):
    def __init__(self, **kwargs):
        html.WebStatus.__init__(self, **kwargs)
        self.putChild("boxes-supported", TenBoxesPerBuilder(categories=['supported']))
        self.putChild("boxes-all", TenBoxesPerBuilder(categories=['supported', 'unsupported']))
        self.putChild("boxes-pyopenssl", TenBoxesPerBuilder(categories=['pyopenssl']))
        self.putChild("supported", WaterfallStatusResource(categories=['supported']))
        self.putChild("waterfall", WaterfallStatusResource(categories=['supported', 'unsupported']))
        self.putChild("waterfall-pyopenssl", WaterfallStatusResource(categories=['pyopenssl']))

        # These are are expensive, so disable them
        # http://trac.buildbot.net/ticket/2268
        self.putChild("grid", Redirect("boxes-supported"))
        self.putChild("tgrid", Redirect("boxes-supported"))
