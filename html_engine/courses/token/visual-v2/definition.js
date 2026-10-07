// Generated offline bundle. Rebuild with node build-definition.cjs.
window.TokenVisualDefinition = {
  "format": "hps.visual-study",
  "version": "0.1.0",
  "revision": 4,
  "status": "G2-assistant-selected; G3-conditional; G4-built; G5-verified; user-visual-review-pending",
  "canvas": [
    1600,
    900
  ],
  "style": {
    "reference": "../../../../docs/styles/science-explainer/references/user-style-reference.png",
    "palette": {
      "paper": "#FBFAF7",
      "ink": "#465B73",
      "coral": "#F47F94",
      "blue": "#B8CAF1",
      "lavender": "#D4C4EF"
    },
    "font": "Microsoft YaHei",
    "imageLanguage": "soft pastel dimensional science illustration"
  },
  "sceneList": [
    {
      "id": "definition",
      "title": "Token：文字进入模型的第一步",
      "layout": "horizontal-pipeline",
      "durationMs": 16000,
      "objects": [
        {
          "id": "source",
          "implementation": "html",
          "role": "original text",
          "box": [
            110,
            315,
            350,
            120
          ],
          "content": "Hello world!"
        },
        {
          "id": "fragments",
          "implementation": "html",
          "role": "3 separately moving tokens",
          "box": [
            100,
            510,
            490,
            76
          ],
          "content": [
            "Hello",
            "␠world",
            "!"
          ]
        },
        {
          "id": "model",
          "implementation": "image",
          "resource": "core",
          "box": [
            660,
            305,
            330,
            340
          ],
          "role": "model computation illustration, not actual internal structure"
        },
        {
          "id": "ids",
          "implementation": "html",
          "box": [
            680,
            650,
            310,
            60
          ],
          "content": "9906 · 1917 · 0"
        },
        {
          "id": "vectors",
          "implementation": "svg",
          "box": [
            1140,
            345,
            330,
            260
          ],
          "role": "symbolic vector bars, not measured values"
        },
        {
          "id": "flow",
          "implementation": "svg",
          "role": "exact directional arrows, temporary motion trails"
        },
        {
          "id": "conclusion",
          "implementation": "html",
          "box": [
            100,
            755,
            1400,
            65
          ],
          "content": "文字 → Token 编号 → 向量表示"
        }
      ],
      "beats": [
        {
          "atMs": 0,
          "untilMs": 4500,
          "caption": "先把文本切成 Token。",
          "narration": "Token 是模型处理文本所用的基本单位。分词器先把文本编码为一串 token；边界由分词规则决定，并不等同于人类语言里的单词。"
        },
        {
          "atMs": 4500,
          "untilMs": 10000,
          "caption": "每个 Token 对应词表编号。",
          "narration": "切分后，每个 token 都有词表中的编号。模型的输入是这些编号，而不是把整句话直接作为一个不可分的对象处理。"
        },
        {
          "atMs": 10000,
          "untilMs": 16000,
          "caption": "编号映射为向量，再进入模型计算。",
          "narration": "模型通过嵌入层把 token 编号映射为向量，再结合上下文进行计算。文本、编号与向量是不同层次，不能把 token 和向量视为同一个东西。"
        }
      ],
      "keyframes": [
        0,
        3500,
        8500,
        14500,
        16000
      ],
      "motion": "source fades in; three code token pills appear separately; transient duplicate pills move toward core at 5–9s and disappear; original pills remain readable; ids then vectors reveal"
    },
    {
      "id": "splitting",
      "title": "一个字，不一定是一个 Token",
      "layout": "editorial-comparison",
      "durationMs": 15000,
      "objects": [
        {
          "id": "english",
          "implementation": "html",
          "box": [
            110,
            270,
            1380,
            200
          ],
          "content": "Hello world! → Hello | ␠world | ! → 3 Token"
        },
        {
          "id": "chinese",
          "implementation": "html",
          "box": [
            110,
            520,
            980,
            170
          ],
          "content": "人工智能很有趣：7 个汉字 → 10 Token"
        },
        {
          "id": "byteTiles",
          "implementation": "svg",
          "box": [
            610,
            615,
            850,
            50
          ],
          "role": "10 token slots labeled with true token IDs; no false Chinese segmentation"
        },
        {
          "id": "count",
          "implementation": "html",
          "box": [
            1160,
            500,
            300,
            180
          ],
          "content": "7 ≠ 10"
        },
        {
          "id": "encoding",
          "implementation": "html",
          "box": [
            110,
            740,
            1360,
            65
          ],
          "content": "实测编码 cl100k_base；␠ 表示空格，结果不代表所有模型。"
        }
      ],
      "beats": [
        {
          "atMs": 0,
          "untilMs": 5500,
          "caption": "英文例子保留空格，按真实边界展示。",
          "narration": "使用 cl100k_base，Hello world! 被编码为三个 token：Hello，带前导空格的 world，以及感叹号。画面中的空格符号用于教学展示，原文实际是一个空格。"
        },
        {
          "atMs": 5500,
          "untilMs": 10500,
          "caption": "这 7 个汉字，在本编码下得到 10 个 Token。",
          "narration": "相同编码下，人工智能很有趣共有七个汉字，却得到十个 token。有些 token 只承载一个字符的部分 UTF-8 字节，不能假设每个 token 都能独立显示成一个完整汉字。"
        },
        {
          "atMs": 10500,
          "untilMs": 15000,
          "caption": "部分 Token 是字节片段；精确数量要实测。",
          "narration": "同一编码实测，unhappiness 切成 un、h 和 appiness，共三个 token。因此原稿中的 un 加 happiness 可以作为假设示意，但不能当作本编码的实测结果。换模型或编码，要重新计算。"
        }
      ],
      "keyframes": [
        0,
        3500,
        8500,
        13500,
        15000
      ],
      "motion": "original sentence first; highlight three true English token boundaries separately; Chinese comparison reveals with ten numbered token tiles; no decorative generated bitmap needed"
    },
    {
      "id": "billing",
      "title": "输入与输出，都要算用量",
      "layout": "bilateral-model-flow",
      "durationMs": 16000,
      "objects": [
        {
          "id": "input",
          "implementation": "html",
          "box": [
            110,
            310,
            390,
            230
          ],
          "content": "输入 120 Token（示意）"
        },
        {
          "id": "output",
          "implementation": "html",
          "box": [
            1090,
            310,
            390,
            230
          ],
          "content": "输出 80 Token（示意）"
        },
        {
          "id": "model",
          "implementation": "image",
          "resource": "billing-core",
          "box": [
            620,
            265,
            370,
            400
          ]
        },
        {
          "id": "arrows",
          "implementation": "svg",
          "role": "input→model→output"
        },
        {
          "id": "movingUnits",
          "implementation": "svg",
          "role": "transient symbolic token pieces; not 200 individually counted particles"
        },
        {
          "id": "formula",
          "implementation": "html",
          "box": [
            170,
            680,
            1260,
            90
          ],
          "content": "费用示意 = 输入量 × 输入单价 + 输出量 × 输出单价"
        },
        {
          "id": "note",
          "implementation": "html",
          "box": [
            110,
            790,
            1380,
            55
          ],
          "content": "缓存、推理及工具等按服务规则计费；不展示实时价格。"
        }
      ],
      "beats": [
        {
          "atMs": 0,
          "untilMs": 5000,
          "caption": "系统指令、历史和问题等都可能计入输入。",
          "narration": "很多文本模型 API 按 token 用量计费。输入不仅是新问题，还可能包括系统指令、历史消息和工具定义等。具体统计和计价以服务说明为准。"
        },
        {
          "atMs": 5000,
          "untilMs": 10000,
          "caption": "模型的回答也会产生输出用量。",
          "narration": "模型输出的回答通常也按 token 计量。不同服务对缓存、推理和工具调用等可能有不同规则，输入与输出单价也可能不同，所以不能只把两个数量相加后乘同一价格。"
        },
        {
          "atMs": 10000,
          "untilMs": 16000,
          "caption": "输入与输出单价分别核对，不能统一乘一个价格。",
          "narration": "简单文字请求的费用，可以用输入数量乘输入单价，加输出数量乘输出单价理解。这只是基础示意，不提供实时价格，也不涵盖所有缓存和推理计费情形。"
        }
      ],
      "keyframes": [
        0,
        3500,
        8500,
        14500,
        16000
      ],
      "motion": "input panel appears; code packets flow into core; output panel appears with outward packets; formula resolves then holds"
    },
    {
      "id": "context",
      "title": "上下文，是一份容量预算",
      "layout": "capacity-laboratory",
      "durationMs": 18000,
      "objects": [
        {
          "id": "capacity",
          "implementation": "svg",
          "box": [
            160,
            335,
            1200,
            150
          ],
          "role": "4,000 hypothetical total; segment widths proportional to 1,500 history +500 question +1,000 reserved output; remaining1,000"
        },
        {
          "id": "labels",
          "implementation": "html",
          "role": "exact segment legends and values"
        },
        {
          "id": "occupancy",
          "implementation": "html",
          "box": [
            1100,
            200,
            370,
            80
          ],
          "content": "3,000 / 4,000"
        },
        {
          "id": "overflow",
          "implementation": "svg",
          "role": "attempt +1,500 fills remaining1,000 and exceeds by500; overall attempted4,500"
        },
        {
          "id": "policies",
          "implementation": "html",
          "box": [
            130,
            600,
            1340,
            150
          ],
          "content": [
            "报错",
            "截断",
            "应用压缩"
          ]
        },
        {
          "id": "note",
          "implementation": "html",
          "box": [
            130,
            790,
            1340,
            55
          ],
          "content": "4k仅教学假设；预留回答不是已生成内容，推理预算依模型规则。"
        }
      ],
      "beats": [
        {
          "atMs": 0,
          "untilMs": 6000,
          "caption": "历史和新问题占用输入容量。",
          "narration": "上下文是一次计算可用的容量，不是永久记忆。这里假设总窗口四千 token，用历史一千五百、新问题五百说明输入占用。"
        },
        {
          "atMs": 6000,
          "untilMs": 11000,
          "caption": "还要为回答预留空间；例子总预算为 3,000。",
          "narration": "再为输出预留一千 token，合计预算三千，还余一千。蓝色斜线表示预留，不是已经生成的回答。部分模型还需考虑推理预算，具体以模型规则为准。"
        },
        {
          "atMs": 11000,
          "untilMs": 18000,
          "caption": "继续加入 1,500 会超限，处理方式取决于接口与应用。",
          "narration": "如果在这个预算之外再加入一千五百 token，总预算就达到四千五百，超过四千。处理可能报错、截断或由应用压缩历史，不必然自动忘掉最早对话。"
        }
      ],
      "keyframes": [
        0,
        4000,
        8500,
        14500,
        18000
      ],
      "motion": "segments grow strictly to numeric widths; reserved-output segment hatch distinguish reservation; extra-input ghost shows 4,500>4,000; three policy outcomes reveal; initial capacity stripe remains clearly distinguishable from attempted overflow"
    },
    {
      "id": "takeaways",
      "title": "记住 Token 的三个关键词",
      "layout": "radial-memory-focus",
      "durationMs": 14000,
      "objects": [
        {
          "id": "brain",
          "implementation": "image",
          "resource": "brain",
          "box": [
            590,
            300,
            420,
            420
          ],
          "role": "knowledge metaphor, not biological explanation of LLM"
        },
        {
          "id": "unit",
          "implementation": "html",
          "box": [
            120,
            315,
            390,
            170
          ],
          "content": [
            "文本单元",
            "不等于一个字或一个词"
          ]
        },
        {
          "id": "usage",
          "implementation": "html",
          "box": [
            1110,
            315,
            380,
            170
          ],
          "content": [
            "用量计量",
            "输入、输出分别核对"
          ]
        },
        {
          "id": "window",
          "implementation": "html",
          "box": [
            545,
            690,
            520,
            120
          ],
          "content": [
            "容量预算",
            "上下文不等于永久记忆"
          ]
        },
        {
          "id": "connections",
          "implementation": "svg",
          "role": "three quiet curved relation lines"
        },
        {
          "id": "practice",
          "implementation": "html",
          "box": [
            120,
            820,
            1360,
            45
          ],
          "content": "练习：固定分词器，比较文字、数字、emoji 与空格的 Token 数。"
        }
      ],
      "beats": [
        {
          "atMs": 0,
          "untilMs": 4500,
          "caption": "Token 是模型处理文本的基本单位。",
          "narration": "Token 可以表示词、片段、标点或字节片段。数字、表情、空格和换行也会影响编码数量，但不能假设每个空格或表情固定占一个 token。"
        },
        {
          "atMs": 4500,
          "untilMs": 9000,
          "caption": "它影响用量，实际费用按服务规则核对。",
          "narration": "分词规则因模型或编码而异；也有不同模型共享同一编码。统计时要记下文本、编码名称及版本。本课保留原文、实测编号和完整解码往返证据，避免把猜测当真实分词。"
        },
        {
          "atMs": 9000,
          "untilMs": 14000,
          "caption": "它也影响上下文容量；训练同样使用 Token 序列。",
          "narration": "语言模型在文本训练中也以 token 序列为基础学习。用一句话理解：Token 是模型处理文本的基本单位。实际计费和上下文能力还要结合模型与服务规则，不能从这个比喻推断永久记忆。"
        }
      ],
      "keyframes": [
        0,
        3000,
        7000,
        12000,
        14000
      ],
      "motion": "central brain metaphor enters; three concepts reveal at left/right/bottom; curved lines draw in; final practice prompt replaces temporary caption"
    }
  ],
  "resources": [
    {
      "id": "core",
      "generation": "standalone soft 3D ivory/pastel lavender AI computation module with no letters/numbers; whole silhouette; true alpha; 15% padding",
      "usedBy": [
        "definition"
      ]
    },
    {
      "id": "billing-core",
      "generation": "recreate spherical model device selected in scene3 design; text/particles/trails removed; standalone alpha",
      "usedBy": [
        "billing"
      ],
      "reference": "designs/03-billing.png"
    },
    {
      "id": "brain",
      "generation": "standalone soft 3D pastel coral/lavender brain metaphor, whole silhouette true alpha no text no orbit lines; 15% padding",
      "usedBy": [
        "takeaways"
      ]
    }
  ],
  "facts": {
    "tokenizer": "cl100k_base",
    "library": "tiktoken 0.13.0",
    "englishIds": [
      9906,
      1917,
      0
    ],
    "chineseIds": [
      17792,
      49792,
      45114,
      118,
      27327,
      17599,
      230,
      19361,
      50266,
      96
    ],
    "source": "../tokenizer-evidence.json"
  },
  "scope": "independent design exploration; manual timing; no audio; not production E1/E2 integration",
  "designReview": [
    {
      "scene": "definition",
      "reference": "designs/01-definition.png",
      "reviewer": "assistant",
      "result": "selected-with-adaptations",
      "observations": "Good dimensional module, visual processing chain and hierarchy. Generated globe decoration omitted as unrelated. Generated text is design-only; code owns exact text."
    },
    {
      "scene": "splitting",
      "reference": "designs/02-splitting.png",
      "reviewer": "assistant",
      "result": "selected-with-content-correction",
      "observations": "Strong comparison layout and count contrast. Generated Chinese tile characters are incorrect; replace all ten tile labels with actual token IDs/byte fragments from tokenizer evidence, no invented character mapping."
    },
    {
      "scene": "billing",
      "reference": "designs/03-billing.png",
      "reviewer": "assistant",
      "result": "selected-with-adaptations",
      "observations": "Preserve bilateral traffic/formula composition and spherical model device; generate separate device to match this design. Omit unrelated globes/floating spheres; all labels and traffic remain code."
    },
    {
      "scene": "context",
      "reference": "designs/04-context.png",
      "reviewer": "assistant",
      "result": "selected-with-math-and-wording-correction",
      "observations": "Preserve large translucent capacity tube and three policy outcomes. Code recomputes all proportions: total budget3,000, add1,500=4,500; overflow500, not a full1,500 outside capacity. Correct truncation wording to interface-dependent removal, not always retaining beginning."
    },
    {
      "scene": "takeaways",
      "reference": "designs/05-takeaways.png",
      "reviewer": "assistant",
      "result": "selected-with-adaptations",
      "observations": "Preserve central dimensional brain and radial concept composition; concise code text replaces extra paragraphs and misleading memory claim. Brain metaphor explicitly not literal model anatomy."
    }
  ],
  "geometryAuthority": {
    "planning": "objects[].box records G1 design intent, not final runtime geometry",
    "actual": "evidence/actual-geometry.json records G4 final rectangles by stable implementation ID; player.js owns the experiment coordinates",
    "productionGap": "Manual recreation, not an automated design-image-to-HTML conversion or production schema. Mapping these layouts into E2 is conditional on user visual approval."
  }
};
