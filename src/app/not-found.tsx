import Link from 'next/link';

export default function NotFound() {
  return (
    <section className="section">
      <div className="container">
        <h1 className="detail__title">页面不存在</h1>
        <p className="detail__lead prose">
          链接可能已变更。可以回到首页，或在作品索引里搜索。
        </p>
        <ul className="hero__actions">
          <li>
            <Link className="button button--primary" href="/">
              回到首页
            </Link>
          </li>
          <li>
            <Link className="button" href="/works">
              浏览作品
            </Link>
          </li>
        </ul>
      </div>
    </section>
  );
}
