// 由 config/distribution.json 确定性生成，请勿手工编辑。
// 必须先于 flow.js / workflow_state.js 加载：flow.js 的
// PPTFlow.distributionFeatures() 是发行功能剖面的唯一读取口。
// 源码检出（无发行配置）保持完整功能，仅显式 false 才视为关闭。
(function (scope) {
  'use strict';

  var FEATURES = Object.freeze({
    digital_human: true,
    handwritten_annotations: true
  });

  var EDITION = 'source';

  scope.PPTStudioDistribution = Object.freeze({
    edition: EDITION,
    schema_version: null,
    features: FEATURES
  });
})(typeof globalThis !== 'undefined' ? globalThis : this);
