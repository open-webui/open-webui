# Citation Snippets

Open WebUI can display inline citations with preview snippets. To enable this feature, your model or tool must return a message that includes both the main text and an accompanying `sources` array.

## Message format

```jsonc
{
  "content": "Answer referencing a report [1] and an article [2].",
  "sources": [
    {
      "source": { "name": "Report.pdf", "url": "https://example.com/report" },
      "document": ["Relevant excerpt from the report…"],
      "metadata": [{ "source": "Report.pdf", "page": 4 }],
      "distances": [0.87]   // optional relevance scores
    },
    {
      "source": { "name": "Article A" },      // `url` is optional
      "document": ["Excerpt from Article A…"],
      "metadata": [{ "source": "Article A" }]
    }
  ]
}
```

* Insert numbered references (`[1]`, `[2]`, …) in the `content` where you want to cite a source.
* Each item in `sources` provides the snippet shown when hovering over the citation marker.
* `document` contains the snippet text, while `metadata` can hold details like `page` or `name`.
* The `distances` field is optional and can be used to store relevance scores.

## Streaming events

If you emit responses incrementally, send a `source` event for each citation so the backend can append it to the message:

```python
await event_emitter({
    "type": "source",  # or "citation" for legacy support
    "data": {
        "source": {"name": "Report.pdf", "url": "https://example.com/report"},
        "document": ["Relevant excerpt from the report…"],
        "metadata": [{"source": "Report.pdf", "page": 4}]
    }
})
```

With this structure in place, Open WebUI replaces the `[n]` markers with interactive elements that reveal the corresponding snippet when hovered.

