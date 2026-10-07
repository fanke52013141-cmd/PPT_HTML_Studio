window.trialContent = {
  "schemaStatus": "experimental evidence, not production scene schema",
  "contractVersion": "0.6.0",
  "title": {
    "screen": "蒸发与凝结",
    "implementation": "html",
    "target": "page.title"
  },
  "subtitle": {
    "screen": "水的两种变化，方向恰好相反",
    "implementation": "html"
  },
  "objects": [
    {
      "id": "left",
      "name": "蒸发",
      "from": "液态",
      "to": "气态",
      "body": "水不沸腾，也会蒸发。",
      "figure": "evaporation-alpha.png",
      "narration": "液态水变成水蒸气，这个过程叫蒸发。蒸发可以在没有沸腾时发生。图中的小球只是水分子示意，水蒸气通常不可见。"
    },
    {
      "id": "right",
      "name": "凝结",
      "from": "气态",
      "to": "液态",
      "body": "冷杯外的水滴，来自空气中的水蒸气。",
      "figure": "condensation-alpha.png",
      "narration": "水蒸气变成液态水，叫凝结。冷杯外的水滴来自空气中的水蒸气，不是杯里的水漏了出来。"
    }
  ],
  "source": {
    "screen": "水分子仅为示意；水蒸气通常不可见。知识依据：USGS 水循环。",
    "implementation": "html",
    "sourceDocument": "../../content-sources.md"
  },
  "spokenOnly": [
    "完整机制解释由讲稿保留；不默认附加生活例子卡",
    "本实验不合成新音频"
  ],
  "directionImplementation": "html inline SVG; not baked into illustration",
  "userVisualReview": "pending"
};
