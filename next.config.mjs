/**
 * Next 15 静态导出配置。
 *
 * ★ 本站部署目标是 GitHub Pages（纯静态托管），因此 `output: 'export'` 是硬约束：
 *   任何 SSR / 服务端特性（Route Handler、tRPC、服务端 env 校验）都不得保留。
 *   本骨架刻意不取 app-c-next-antd 模板的 tRPC / @t3-oss/env-nextjs 部分。
 *
 * ★ `trailingSlash: true` —— Pages 上 `/works/x` 需落到 `out/works/x/index.html`。
 * ★ `images.unoptimized` —— 静态导出不支持 Next 图像优化服务。
 *
 * @type {import('next').NextConfig}
 */
const nextConfig = {
  output: 'export',
  trailingSlash: true,
  images: { unoptimized: true },
  reactStrictMode: true,
};

export default nextConfig;
