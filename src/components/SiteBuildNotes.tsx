import { Disclosure } from '@/components/Disclosure';
import { StructureFigure } from '@/components/figures/StructureFigure';
import { loadGateManifest } from '@/lib/build-notes';

/**
 * 首页「本站是怎么做的」区块（第三批）。
 *
 * ★ 为什么这块内容落在首页：本站的读者定位是**技术同行与开源协作者**，
 *   而「这套站点自身如何被工程化」在其他四页**命中 0 次**（实产物普查），
 *   因此它是真正的**唯一落点**新内容，不是把已移出首页的区块回填。
 *   它同时是 D4「本站充当前端能力系统的首个真实调用方」的呈现面。
 *
 * ★ 可读性（第三批修订）：初版把脚本路径与清单**平铺**在首屏，被走查判为不可读。
 *   现改为**渐进披露**：首屏只留三句人话，明细折进 <details>（复用 `Disclosure`，
 *   原生元素 ⇒ 无 JS 可用、键盘可达）。「渐进披露」本就在第一批已选的交互项内。
 *
 * ★ 数字纪律：本区块**不复述任何计数**（不写「四道门控」「三条记录」），
 *   明细由 `scripts/gate-manifest.json` **派生渲染** ⇒ 增删门控只改清单，
 *   ⛔ 不产生会腐化的字面常量（一致性由 `gate_ia_division.py` 的 A7/A8 机检）。
 */
export function SiteBuildNotes() {
  const manifest = loadGateManifest();

  return (
    <section id="build-notes" className="section section--tight" data-reveal>
      <div className="container">
        <header className="section__head">
          <h2 className="section__title">本站是怎么做的</h2>
          <p className="section__subtitle">这套站点自身即作品，也是前端能力系统的首个真实调用方</p>
        </header>

        {/* ★ 结构优先：这条链是「源 → 管道 → 产物 → 呈现」的有向链，
            链式结构的正确表达是图，⛔ 不是又一段分点文字。图只写角色与流向，不写计数。 */}
        <figure className="figure">
          <div className="figure__frame">
            <StructureFigure />
          </div>
          <figcaption className="figure__caption">
            上面这张图是本页要说的全部：左侧是源，中间是管道，右侧是产物与呈现面。
            下方的三条只是把同一件事讲成句子；两处⛔ 不各说一遍细节。
          </figcaption>
        </figure>

        <ul className="notes notes--plain">
          <li>
            数据每日从各项目仓库重采，指标在<strong>构建期</strong>算完再纯静态导出——
            运行时不发任何数据请求，无 JS 也能读到全部内容。
          </li>
          <li>
            门控一律读<strong>真实产物</strong>（样式令牌 / 导出结果 / 指标登记），不读源码自述；
            每道都内置<strong>负向夹具</strong>，用来证明判据不是恒真。
          </li>
          <li>
            所有数据与图形都在本地可复现：取用的能力层记录与产物一一对应，
            清单与仓库不一致时<strong>构建直接失败</strong>。
          </li>
        </ul>

        <Disclosure summary="门控清单与能力层取用明细" hint="可展开">
          <h3 className="about__label">门控 · 读什么，怎么证明判据可判假</h3>
          <ul className="notes">
            {manifest.gates.map((gate) => (
              <li key={gate.script}>
                <code>{gate.script}</code> —— 读 {gate.reads}
                {gate.selftest ? ' · 含 --selftest 负向夹具' : null}
              </li>
            ))}
          </ul>

          <h3 className="about__label">能力层取用 · 记录 → 产物</h3>
          <ul className="notes">
            {manifest.capability_uses.map((use) => (
              <li key={use.key}>
                <code>{use.key}</code> → <code>{use.artifact}</code> —— {use.note}
              </li>
            ))}
          </ul>

          <p className="detail__note">
            上表由 <code>scripts/gate-manifest.json</code> 派生；清单与 <code>scripts/</code>
            实际集合的一致性由门控机检（漏登记即构建失败），因此这里不会出现与仓库不符的陈述。
          </p>
        </Disclosure>
      </div>
    </section>
  );
}
