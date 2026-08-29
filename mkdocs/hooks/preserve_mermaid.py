"""Protect Mermaid source whitespace before the HTML minifier runs."""

from mkdocs.plugins import event_priority


@event_priority(100)
def on_post_page(output, **kwargs):
    """Mark Mermaid containers as preformatted for htmlmin.

    htmlmin removes the temporary ``pre`` attribute while preserving the
    element's whitespace, leaving the published markup unchanged except for
    its significant Mermaid line breaks.
    """
    return output.replace('<div class="mermaid">', '<div pre class="mermaid">')
