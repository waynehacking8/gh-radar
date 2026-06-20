# GitHub Radar — 2026-06-20

_50 new tools surfaced from Hacker News, new repos, Trending, X._

### 1. [affaan-m/ECC](https://github.com/affaan-m/ECC)
⭐ 218,380 · 𝕏 @dotey · JavaScript

> ECC 是專為 Claude Code、Codex、Cursor 等 AI 編程工具設計的 Agent Harness 優化系統，整合技能管理、長期記憶與安全機制。隨著 Codex 推出 Handoff 功能，讓開發者用自然語言把進行中的任務連同完整 Git 狀態遷移到遠端主機繼續執行，Agent 執行層的穩定性與效能需求愈發迫切。ECC 的目標正是讓這類跨設備 AI 代理任務跑得更快、更可靠。
> _The agent harness performance optimization system. Skills, instincts, memory, security, and research-first development for Claude Code, Codex, Opencode, Cursor and beyond._

> 💬 @dotey：「Codex 上线了一个跨设备任务迁移功能，叫 Handoff。你在笔记本上用 Codex 写代码写到一半，合上盖子之前，可以把正在进行的任务连同代码状态一起迁移到远程服务器上继续跑。回到家了，再把任务拉回来。 > 这个功能有两个有意思的地方。 > 第一，迁移操作不是在界面上点按钮，而是直接在聊天框里用自然语言下指令。…」

📍 出處 / via: Firecrawl → X @dotey

[X post](https://x.com/dotey/status/2068183780938985827)

### 2. [kyverno/kyverno](https://github.com/kyverno/kyverno)
⭐ 7,857 · 🔥 9/day · Go

> Kyverno 是 Kubernetes 原生的策略引擎，以 YAML 格式定義叢集安全與合規規範，無需學習額外的程式語言。它能在資源建立時自動驗證、修改或產生 Kubernetes 物件，涵蓋映像檔驗證、Pod 安全設定等常見場景。想在多個叢集統一落實 Policy as Code 的維運團隊，Kyverno 是目前最廣泛採用的開源選擇之一。
> _Unified Policy as Code_

📍 出處 / via: GitHub Trending

### 3. [argoproj/argo-cd](https://github.com/argoproj/argo-cd)
⭐ 23,188 · 🔥 8/day · Go

> Argo CD 是 Kubernetes 的宣告式持續部署工具，以 Git 儲存庫為唯一事實來源，讓叢集狀態自動與版本控制同步。手動部署容易造成設定漂移，Argo CD 的 GitOps 流程能即時偵測差異並自動還原或同步。它是目前最成熟的開源 GitOps 方案，廣泛用於生產環境的 Kubernetes 部署自動化。
> _Declarative Continuous Deployment for Kubernetes_

📍 出處 / via: GitHub Trending

### 4. [RocketChat/Rocket.Chat](https://github.com/RocketChat/Rocket.Chat)
⭐ 45,678 · 🔥 8/day · TypeScript

> Rocket.Chat 是開源的企業安全通訊平台，支援完全自架部署以確保資料留在組織內部，適合對合規要求嚴格的場景。它整合即時訊息、視訊通話與全頻道客服，可作為 Slack 等 SaaS 服務的自主替代方案。對於不願將敏感通訊資料交給第三方的企業，Rocket.Chat 提供了完整的控制權。
> _The Secure CommsOS™ for mission-critical operations_

📍 出處 / via: GitHub Trending

### 5. [alibaba/MNN](https://github.com/alibaba/MNN)
⭐ 15,519 · 🔥 8/day · C++

> MNN 是阿里巴巴開源的輕量推理引擎，專為行動裝置與邊緣端場景設計，能在資源有限的設備上高效運行 LLM 與 AI 模型。它針對 ARM 等多種硬體架構深度優化，已通過阿里巴巴大規模生產環境長期驗證。對需要在端側部署 AI 推理、不依賴雲端的開發者而言，MNN 是效能與輕量兼具的成熟選擇。
> _MNN: A blazing-fast, lightweight inference engine battle-tested by Alibaba, powering high-performance on-device LLMs and Edge AI._

📍 出處 / via: GitHub Trending

### 6. [facebook/rocksdb](https://github.com/facebook/rocksdb)
⭐ 31,787 · 🔥 7/day · C++

> RocksDB 是 Facebook 開源的嵌入式持久化鍵值引擎，基於 LSM Tree 架構針對 SSD 高速寫入優化，適合需要低延遲本地儲存的高效能應用。它廣泛被用作 TiKV 等分散式系統的底層儲存引擎，已在大規模生產環境中驗證。當應用需要在進程內嵌入高效能持久儲存時，RocksDB 是最成熟的開源選擇。
> _A library that provides an embeddable, persistent key-value store for fast storage._

📍 出處 / via: GitHub Trending

### 7. [TheOdinProject/curriculum](https://github.com/TheOdinProject/curriculum)
⭐ 12,681 · 🔥 7/day · JavaScript

> The Odin Project 是完全免費的開源網頁開發課程，涵蓋從 HTML/CSS 基礎到 JavaScript 與 Ruby on Rails 的完整學習路徑。所有內容透過 GitHub 公開維護，學習者與社群成員均可直接貢獻改進。對想自學成為全端工程師但預算有限的人而言，這是評價最高的免費資源之一。
> _The open curriculum for learning web development_

📍 出處 / via: GitHub Trending

### 8. [vercel/eve](https://github.com/vercel/eve)
⭐ 1,692 · 🆕 new · TypeScript

> Eve 是 Vercel 推出的 Agent 建構框架，提供標準化的方式來定義、組合與部署 AI Agent 工作流程。隨著 Agent 應用快速普及，缺乏統一抽象層的問題愈加明顯，Eve 試圖以框架形式填補這個缺口。作為 Vercel 生態的一環，它讓開發者能更快將 Agent 功能帶入生產環境。
> _The Framework for Building Agents_

📍 出處 / via: GitHub new-repo search

### 9. [lenucksi/aur-malware-check](https://github.com/lenucksi/aur-malware-check)
⭐ 1,605 · 🆕 new · Shell

> 2026 年 6 月 AUR 爆發 atomic-lockfile 供應鏈攻擊，惡意套件透過竄改鎖定檔案的方式植入惡意程式碼，波及範圍引發社群高度警戒。aur-malware-check 整合了散落在社群 Gist 的各種偵測工具，讓使用者能快速確認系統是否受到感染。對日常依賴 AUR 安裝套件的 Arch Linux 用戶而言，這是目前最直接的自查方式。
> _Detection tools for the June 2026 atomic-lockfile AUR supply-chain attack. Consolidated from community Gists._

📍 出處 / via: GitHub new-repo search

### 10. [musescore/MuseScore](https://github.com/musescore/MuseScore)
⭐ 14,748 · 🔥 6/day · C++

> MuseScore 是功能完整的開源樂譜製作軟體，支援多聲部記譜、MIDI 播放與匯出 PDF、MusicXML 等格式，排版品質接近商業軟體水準。它完全免費，是 Finale、Sibelius 等付費工具的主要開源替代方案。對作曲家、音樂教師或學生而言，MuseScore 是將樂思轉化為正式樂譜最實用的選擇。
> _MuseScore is an open source and free music notation software. For support, contribution, bug reports, visit MuseScore.org. Fork and make pull requests!_

📍 出處 / via: GitHub Trending

### 11. [espressif/arduino-esp32](https://github.com/espressif/arduino-esp32)
⭐ 16,961 · 🔥 6/day · C++

> arduino-esp32 是 Espressif 官方維護的 Arduino 核心，讓開發者以熟悉的 Arduino API 為 ESP32 系列晶片開發 Wi-Fi 與藍牙應用。ESP32 憑藉低成本與豐富的無線連接能力成為 IoT 原型開發的熱門平台，這個函式庫大幅降低了入門門檻。想快速驗證 IoT 概念、不想深入 ESP-IDF 原生框架的開發者，這是最直接的起點。
> _Arduino core for the ESP32 family of SoCs_

📍 出處 / via: GitHub Trending

### 12. [oven-sh/bun](https://github.com/oven-sh/bun)
⭐ 93,322 · 💬 HN 3 · Rust

> Bun 是整合執行環境、打包器、測試工具與套件管理器的 JavaScript 一體化工具，以極速為核心賣點。近期社群發現 Bun 正在進行「vibe-port」——將底層實作從 Zig 遷移至 Rust，引發對效能取捨與語言選擇的廣泛討論。這場架構轉移讓開發者好奇新版本能否延續 Bun 一貫的速度優勢。
> _Incredibly fast JavaScript runtime, bundler, test runner, and package manager – all in one_

📍 出處 / via: Hacker News

[HN](https://news.ycombinator.com/item?id=48597388)

### 13. [apache/datafusion](https://github.com/apache/datafusion)
⭐ 8,900 · 🔥 5/day · Rust

> Apache DataFusion 是以 Rust 撰寫、納入 Apache 基金會的高效能 SQL 查詢引擎，提供向量化執行與原生 Arrow 格式支援。它設計為可嵌入應用程式內部的查詢層，適合需要在服務內直接執行分析查詢而無須部署獨立資料庫的場景。憑藉出色的效能與可擴充架構，在資料工程社群中持續受到關注。
> _Apache DataFusion SQL Query Engine_

📍 出處 / via: GitHub Trending

### 14. [fleetdm/fleet](https://github.com/fleetdm/fleet)
⭐ 6,507 · 🔥 5/day · Go

> Fleet 是一套開源的裝置管理平台，讓 IT 與資安團隊能統一管理跨平台終端設備，涵蓋 macOS、Windows 及 Linux。底層以 osquery 驅動，可即時查詢裝置狀態、推送合規政策並追蹤軟體清單。對重視可見性與自主掌控的企業而言，它是商業 MDM 方案的有力替代選擇。
> _Open device management_

📍 出處 / via: GitHub Trending

### 15. [Waishnav/devspace](https://github.com/Waishnav/devspace)
⭐ 1,483 · 🆕 new · TypeScript

> DevSpace 嘗試將 ChatGPT 改造成類似 GitHub Copilot 的程式碼輔助工具，讓開發者在工作環境中獲得上下文感知的程式建議。對於尚未訂閱 Copilot 卻已有 ChatGPT 存取權限的工程師來說，這是一條低成本切入 AI 程式輔助的捷徑。專案目標是縮短通用聊天介面與專業編碼助手之間的差距。
> _Turn ChatGPT into Codex_

📍 出處 / via: GitHub new-repo search

### 16. [SkyBlue997/enableMacosAI](https://github.com/SkyBlue997/enableMacosAI)
⭐ 1,442 · 🆕 new · Shell

> 這個工具針對國行版 Mac 的地區限制，提供一鍵腳本讓使用者在 macOS 27 及搭載 Apple Silicon 的機器上啟用完整的 Apple 智慧功能，同時涵蓋裝置端推論與 Private Cloud Compute 雲端運算兩個層面。由於 Apple Intelligence 在中國大陸受到地區封鎖，許多用戶無法透過正常管道使用，這個開源方案因此引起廣泛討論。有意嘗試者應事先評估相關風險與合規疑慮。
> _国行 Mac 一键开启完整 Apple 智能(端侧 + Private Cloud Compute 云端)· macOS 27 / Apple Silicon_

📍 出處 / via: GitHub new-repo search

### 17. [k0sproject/k0s](https://github.com/k0sproject/k0s)
⭐ 6,286 · 🔥 4/day · Go

> k0s 是一套「零摩擦」Kubernetes 發行版，將所有元件打包成單一靜態執行檔，大幅簡化安裝與維運流程。無論是邊緣運算、CI 環境或資源受限的伺服器，都能在數分鐘內啟動完整的 Kubernetes 叢集，不需額外處理複雜的依賴關係。它特別適合希望享有 Kubernetes 生態系卻不想承擔繁瑣部署負擔的團隊。
> _k0s - The Zero Friction Kubernetes_

📍 出處 / via: GitHub Trending

### 18. [facebook/folly](https://github.com/facebook/folly)
⭐ 30,425 · 🔥 4/day · C++

> Folly 是 Meta 內部長期開發並實際用於生產環境的 C++ 工具函式庫，提供高效能的資料結構、並發原語與記憶體管理工具。它填補了 C++ 標準函式庫的不足，尤其在大規模、高並發的系統開發場景中被廣泛採用。對需要工業級 C++ 基礎設施的團隊而言，Folly 是歷經考驗的成熟選擇。
> _An open-source C++ library developed and used at Facebook._

📍 出處 / via: GitHub Trending

### 19. [doctest/doctest](https://github.com/doctest/doctest)
⭐ 6,781 · 🔥 4/day · C++

> doctest 以單一標頭檔的形式提供功能完整的 C++ 測試框架，支援 C++11 至 C++23，並以極短的編譯時間著稱。它允許開發者將測試直接嵌入正式程式碼旁邊，降低維護分離測試專案的心理負擔。輕量的設計使其特別受到重視編譯速度與零外部依賴的 C++ 專案青睞。
> _The fastest feature-rich C++11/14/17/20/23 single-header testing framework_

📍 出處 / via: GitHub Trending

### 20. [fmtlib/fmt](https://github.com/fmtlib/fmt)
⭐ 23,608 · 🔥 4/day · C++

> fmt 是現代 C++ 的格式化函式庫，提供比 printf 更安全、比 iostream 更直觀的字串格式化介面，並已成為 C++20 std::format 的實作基礎之一。它以高效能與型別安全為核心設計目標，廣泛用於日誌輸出、CLI 工具與資料序列化等場景。在 C++ 社群中，fmt 幾乎已是格式化輸出的事實標準。
> _A modern formatting library_

📍 出處 / via: GitHub Trending

### 21. [huggingface/transformers.js](https://github.com/huggingface/transformers.js)
⭐ 16,127 · 💬 HN 2 · JavaScript

> Transformers.js 4.0.0 是一個重要里程碑版本，讓開發者能直接在瀏覽器端執行 Hugging Face 的 Transformer 模型，完全無需後端伺服器支援。此次大版本更新帶來更廣泛的模型相容性與效能改進，進一步降低在網頁應用中整合機器學習能力的門檻。對於希望在前端提供 AI 功能卻不想維運推論伺服器的開發者而言，這個版本值得重點關注。
> _State-of-the-art Machine Learning for the web. Run 🤗 Transformers directly in your browser, with no need for a server!_

📍 出處 / via: Hacker News

[HN](https://news.ycombinator.com/item?id=48606688)

### 22. [excalidraw/excalidraw](https://github.com/excalidraw/excalidraw)
⭐ 125,679 · 💬 HN 2 · TypeScript

> Excalidraw 是一款以手繪風格呈現的虛擬白板工具，讓使用者能快速繪製架構圖、流程圖與概念草稿，視覺上保有隨手勾勒的親切感而非嚴謹的工程製圖風格。它支援即時協作，非常適合遠端團隊在討論技術設計時作為輕量的視覺溝通媒介。開源社群的持續貢獻，也讓它成為許多開發者日常筆記的常備工具。
> _Virtual whiteboard for sketching hand-drawn like diagrams_

📍 出處 / via: Hacker News

[HN](https://news.ycombinator.com/item?id=48606560)

### 23. [littlefs-project/littlefs](https://github.com/littlefs-project/littlefs)
⭐ 6,738 · 💬 HN 2 · C

> littlefs 是專為微控制器環境設計的小型容錯檔案系統，能在 Flash 儲存媒體上安全運作，並具備掉電保護與磨損平均的能力。近期有人分享了深入探討其設計原理的文章，引發工程師對嵌入式儲存機制的廣泛討論。在資源極度受限且可靠性至關重要的 IoT 裝置開發中，littlefs 是備受信賴的選擇。
> _A little fail-safe filesystem designed for microcontrollers_

📍 出處 / via: Hacker News

[HN](https://news.ycombinator.com/item?id=48597690)

### 24. [google/googletest](https://github.com/google/googletest)
⭐ 38,725 · 🔥 3/day · C++

> GoogleTest 是 Google 開源的 C++ 測試與 Mock 框架，以豐富的 assertion 巨集與彈性的測試結構廣受採用，也是許多大型開源 C++ 專案的標配測試工具。它支援參數化測試與死亡測試等進階功能，並與各種 CI 系統良好整合。對於需要在 C++ 專案中建立系統化測試文化的團隊，GoogleTest 提供了成熟且文件完整的起點。
> _GoogleTest - Google Testing and Mocking Framework_

📍 出處 / via: GitHub Trending

### 25. [loc567/loc567](https://github.com/loc567/loc567)
⭐ 1,227 · 🆕 new · C

> 一款完全開源免費的純網頁端 iOS 模擬定位工具，無需越獄或安裝任何 App，直接在瀏覽器中操作即可改變裝置回報的 GPS 位置。適合需要測試定位功能的 App 開發者，也適用於任何想在不動手機的情況下模擬所在地點的使用者。官方提供線上體驗網址，進一步降低了嘗試門檻。
> _loc567 是一款完全开源免费的纯网页端iOS模拟定位工具。在线体验地址：https://loc567.com_

📍 出處 / via: GitHub new-repo search

### 26. [MystenLabs/sui](https://github.com/MystenLabs/sui)
⭐ 7,716 · 🔥 2/day · Rust

> Sui 是 Mysten Labs 推出的新世代智能合約平台，採用 Move 語言的資產導向程式模型，以高吞吐量與低延遲著稱。它將物件所有權視為核心抽象，使彼此獨立的交易能夠平行執行而不互相阻塞，大幅提升鏈上處理效率。這套設計在 DeFi 與遊戲等高頻互動場景中展現出明顯優勢，是以太坊生態之外值得關注的替代選項。
> _Sui, a next-generation smart contract platform with high throughput, low latency, and an asset-oriented programming model powered by the Move programming language_

📍 出處 / via: GitHub Trending

### 27. [apache/arrow](https://github.com/apache/arrow)
⭐ 16,856 · 🔥 2/day · C++

> Apache Arrow 定義了一套跨語言的記憶體內欄位格式，讓 Python、Java、Rust 等不同生態系的資料工具能以零拷貝方式共享資料，消除序列化與反序列化的開銷。它已成為 Spark、DuckDB、Pandas 等現代分析工具之間資料交換的事實標準。在多語言資料工程管線日益普及的今天，Arrow 是高效跨系統互通不可或缺的基礎建設。
> _Apache Arrow is the universal columnar format and multi-language toolbox for fast data interchange and in-memory analytics_

📍 出處 / via: GitHub Trending

### 28. [srush/gpu-puzzles](https://github.com/srush/GPU-Puzzles)
⭐ 12,238 · 💬 HN 1 · Jupyter Notebook

> GPU Puzzles 是一套以 Python 撰寫的 CUDA 學習謎題集，要求解題者直接操作 thread、block 與共享記憶體，而非仰賴高層框架的抽象封裝。透過解謎的方式，開發者能循序漸進地建立 GPU 並行程式設計的底層直覺。這個 2021 年的專案近期再度浮上話題，反映出社群對 GPU 核心知識的持續渴求。
> _Solve puzzles. Learn CUDA._

📍 出處 / via: Hacker News

[HN](https://news.ycombinator.com/item?id=48604398)

### 29. [entireio/cli](https://github.com/entireio/cli)
⭐ 4,533 · 🔥 6/day · Go

> Entire CLI 會在日常的 Git 工作流程中自動捕捉 AI 代理的操作 session，並將記錄與 commit 一同建立索引，讓「這段程式碼是怎麼寫出來的」成為可搜尋的開發歷史。對於需要程式碼審計、知識傳承或 AI 協作透明度的團隊，這提供了一層額外的可追蹤性。它尤其適合 AI 代理大量介入開發流程的現代工作環境。
> _📜 Entire CLI hooks into your Git workflow to capture AI agent sessions as you work. Sessions are indexed alongside commits, creating a searchable record of how code was written in your repo._

📍 出處 / via: GitHub Trending

### 30. [EEliberto/IPA-Download](https://github.com/EEliberto/IPA-Download)
⭐ 1,125 · 🆕 new · Swift

> 這個工具讓使用者能夠取得 iOS App 的歷史版本 IPA 檔案，下載後可直接透過 AirDrop 傳輸到 iPhone 或 iPad 上安裝，操作流程簡便直接。主要應用情境包括逆向工程分析、舊版行為測試，以及自動化封包擷取等資安研究工作。對於需要重現特定版本 App 行為的開發者與安全研究人員，是一個實用的輔助工具。
> _一款用于安装 IPA 历史版本的工具，适用于获取旧版应用并自动捕获数据包。下载后，可直接通过 AirDrop 传输至 iPhone、iPad 上并安装并使用。_

📍 出處 / via: GitHub new-repo search

### 31. [levy-street/world-of-claudecraft](https://github.com/levy-street/world-of-claudecraft)
⭐ 1,042 · 🆕 new · TypeScript

> 這個專案以「Claude」與「craft」組合命名，暗示是一個以 Claude AI 為核心驅動的創作或互動體驗，目前尚無公開的詳細說明。從命名風格判斷，可能是某種 AI 驅動的世界建構或實驗性互動環境。吸引開發者目光的，或許正是它結合 AI 能力與創作主題所帶來的想像空間。

📍 出處 / via: GitHub new-repo search

### 32. [Mathieu2301/TradingView-API](https://github.com/Mathieu2301/TradingView-API)
⭐ 3,906 · 🔥 11/day · JavaScript

> 這個非官方函式庫讓開發者能夠以程式方式從 TradingView 取得即時股票報價資料，不需依賴官方付費訂閱方案。對於想自建股價監控系統、量化交易看板或價格警示機器人的個人開發者，它填補了官方 API 缺席的空白。在量化交易社群中持續受到關注，因為它提供了低成本取得市場即時資料的可行路徑。
> _📈 Get real-time stocks from TradingView_

📍 出處 / via: GitHub Trending

### 33. [chromiumembedded/cef](https://github.com/chromiumembedded/cef)
⭐ 4,604 · 💬 HN 2 · C++

> Chromium Embedded Framework（CEF）讓開發者能夠將完整的 Chromium 瀏覽器核心嵌入到桌面應用程式中，輕鬆實現網頁內容渲染與 JavaScript 執行能力。許多知名桌面軟體透過 CEF 顯示網頁介面，是業界長期驗證、成熟穩定的選擇。對於需要在原生應用內整合網頁技術的開發者，CEF 至今仍是最廣泛採用的解決方案之一。
> _Chromium Embedded Framework (CEF). A simple framework for embedding Chromium-based browsers in other applications._

📍 出處 / via: Hacker News

[HN](https://news.ycombinator.com/item?id=48606387)

### 34. [dbt-labs/dbt-core](https://github.com/dbt-labs/dbt-core)
⭐ 13,035 · 🔥 0/day · Rust

> dbt 讓資料工程師與分析師能夠用 SQL 定義資料轉換邏輯，並套用版本控制、自動化測試、文件產生等軟體工程實踐來管理資料管線。它將零散的 ETL 腳本整理成模組化、可測試的轉換模型，大幅降低資料倉儲的維護複雜度。隨著 Analytics Engineering 概念的普及，dbt 已成為現代資料棧不可缺少的核心工具。
> _dbt enables data analysts and engineers to transform their data using the same practices that software engineers use to build applications._

📍 出處 / via: GitHub Trending

### 35. [nolangz/pixel2motion](https://github.com/nolangz/pixel2motion)
⭐ 830 · 🆕 new · Python

> pixel2motion 是一個 AI 技能，能將靜態點陣圖商標自動轉換為流暢的 SVG 動畫，並同步輸出可嵌入網頁的 HTML 示範、GIF 或影片預覽，以及動態品質確認素材。對於需要快速為品牌視覺加入動態效果的設計師或前端開發者，它大幅縮短了從靜態圖到多格式動態輸出的製作週期。整個流程全自動完成，無需手動逐格調整。
> _AI logo animation skill: turn raster logos into smooth SVG animation, animated HTML demos, GIF/video previews, and motion QA evidence._

📍 出處 / via: GitHub new-repo search

### 36. [orange2ai/renwei-writing](https://github.com/orange2ai/renwei-writing)
⭐ 828 · 🆕 new

> 「人味儿寫作」是一款 AI 代理技能，目標是在協助潤色文章的同時，刻意保留寫作者的個人語氣與風格，而非將文字改寫成千篇一律的 AI 腔調。它針對的是 AI 輔助寫作後文字喪失個性的普遍痛點，強調好的編輯應讓文章「更像你自己寫的」。對於部落客、個人創作者或任何重視文字溫度的使用者，提供了一種更有人情味的 AI 協作方式。
> _人味儿写作 · An AI agent skill: edit people's words without erasing the person behind them_

📍 出處 / via: GitHub new-repo search

### 37. [vorssaint/vorssaint-utils](https://github.com/vorssaint/vorssaint-utils)
⭐ 745 · 🆕 new · Swift

> 免費開源的 macOS 選單列工具組，整合了每個應用程式獨立音量調節、系統監控、防睡眠、視窗切換、書架與應用程式卸載器等多項功能。Mac 使用者不再需要安裝多個付費小工具，透過單一選單列入口即可統一管理常見系統操作，功能齊備且完全免費，因而引起廣泛關注。
> _Free open-source macOS menu bar toolkit. Per-app volume mixer, system monitor, keep awake, window switcher (Alt Tab), shelf, app uninstaller, and much more._

📍 出處 / via: GitHub new-repo search

### 38. [alchaincyf/fanbox](https://github.com/alchaincyf/fanbox)
⭐ 736 · 🆕 new · JavaScript

> 專為「vibe coding」設計的一體化駕駛艙：左側瀏覽專案檔案，右側或下方操控 AI 代理，中間即時呈現每一次程式碼差異。這種佈局讓開發者在 AI 協作過程中無需在多個視窗間切換，能直觀掌握每次改動的前後對比，加速人與 AI 協力開發的反饋迴路。
> _vibe coding 的驾驶舱：左边文件，右边/下边终端，中间看清每一次改动。 / The cockpit for vibe coding: browse files on the left, command agents on the right, watch every change in between._

📍 出處 / via: GitHub new-repo search

### 39. [coder/boo](https://github.com/coder/boo)
⭐ 677 · 🆕 new · Zig

> 由 libghostty 驅動、風格類似 GNU screen 的現代終端機多工器。開發者可在單一視窗內管理多個工作階段與面板，保留了 screen 使用者熟悉的分割與切換邏輯，同時受益於 libghostty 帶來的現代終端機渲染能力。
> _A GNU screen style terminal multiplexer built on libghostty._

📍 出處 / via: GitHub new-repo search

### 40. [joeseesun/qiaomu-goal-meta-skill](https://github.com/joeseesun/qiaomu-goal-meta-skill)
⭐ 667 · 🆕 new · Python

> 能將模糊或複雜的 Codex 任務描述自動規格化的 meta-skill，輸出包含目標結果、驗證條件、限制範圍、迭代策略與完成證據的強健 `/goal` 指令。對於常因任務描述不精確而讓 AI 跑偏的開發者，它相當於一道自動化的任務釐清前置步驟，讓 Codex 執行時更有方向感。
> _Turn vague or complex Codex tasks into strong `/goal` commands with outcome, verification, constraints, boundaries, iteration policy, completion evide_

📍 出處 / via: GitHub new-repo search

### 41. [SunJaycy/GoldenEye-Recomp](https://github.com/SunJaycy/GoldenEye-Recomp)
⭐ 577 · 🆕 new · C

> 從專案名稱判斷，這是對經典射擊遊戲《黃金眼》的重新編譯專案，延續近年社群將老牌遊戲以重編譯方式移植至現代平台的風潮。目標是讓這款傳奇作品以原生應用程式形式執行，不再依賴模擬器，從而獲得更好的相容性與效能。

📍 出處 / via: GitHub new-repo search

### 42. [TestSprite/testsprite-cli](https://github.com/TestSprite/testsprite-cli)
⭐ 561 · 🆕 new · TypeScript

> TestSprite 的官方命令列工具，讓 AI 驅動的自動化測試能直接在終端機中執行，無需額外的圖形介面。適合將 AI 測試整合進 CI/CD 管線或自動化腳本的開發者，CLI 形式大幅降低接入門檻，方便在無介面的伺服器環境中運行。
> _Official TestSprite CLI — AI-powered automated testing from your terminal_

📍 出處 / via: GitHub new-repo search

### 43. [fguzman82/gateGPT](https://github.com/fguzman82/gateGPT)
⭐ 531 · 🆕 new · Verilog

> 以 RTL 硬體描述語言實作完整 Transformer 架構，並燒錄至 Virtex-5 FPGA 上執行，實測推論速度達每秒約 5.6 萬個 token。這個 microGPT 硬體實作展示了在自訂晶片上運行語言模型的可行性，對研究 AI 加速器與邊緣推論的工程師具有重要的實驗參考價值。
> _Full Transformer into a custom chip. microGPT in RTL, generating names on a Virtex-5 FPGA at ~56k tokens/second._

📍 出處 / via: GitHub new-repo search

### 44. [MSNightmare/GreatXML](https://github.com/MSNightmare/GreatXML)
⭐ 529 · 🆕 new

> 揭露一個透過 GreatXML 繞過 BitLocker 磁碟加密的安全漏洞，屬於 XML 解析層面的安全缺陷研究。此案例說明看似無害的 XML 處理邏輯如何成為繞過磁碟加密防護的攻擊入口，對資安研究人員與系統管理員具有重要的警示意義。
> _GreatXML bitlocker bypass vulnerability_

📍 出處 / via: GitHub new-repo search

### 45. [DanMcInerney/architect-loop](https://github.com/DanMcInerney/architect-loop)
⭐ 522 · 🆕 new · HTML

> 以 Claude Fable 5 擔任架構師、GPT-5.5 Codex 擔任實作者的跨廠商 AI 代理協作迴圈，以 Git 儲存庫作為共享記憶體，封裝為 Claude Code skill。兩個來自不同廠商的模型在此框架中明確分工——一負責高層設計決策，另一負責程式碼生成——背後有研究文獻支撐其協作模式。
> _Claude Fable 5 as architect, GPT-5.5 Codex as builder, the repo as memory - a research-backed Claude Code skill for the cross-vendor agent loop_

📍 出處 / via: GitHub new-repo search

### 46. [mrtooher/fable-mode](https://github.com/mrtooher/fable-mode)
⭐ 520 · 🆕 new

> 啟用後讓 Claude 採用 Fable 風格的代理行為：先進行明確的多階段規劃，再將子任務委派給子代理執行，最後進行自我驗證。對希望在 Claude Code 中獲得更結構化、可追蹤執行流程的開發者，這個 skill 提供了一套可控的多步驟任務框架，避免 AI 在複雜任務中跳過規劃直接行動。
> _A Claude skill that activates Fable-style agentic behavior: explicit multi-stage planning, sub-agent delegation, and self-verification._

📍 出處 / via: GitHub new-repo search

### 47. [NO6KIKO/gorest-2d-animation-spritesheet-generator](https://github.com/NO6KIKO/gorest-2d-animation-spritesheet-generator)
⭐ 520 · 🆕 new · TypeScript

> 由 Codex 輔助開發的本地端 2D 動畫 Spritesheet 產生器，同時具備場景合成工作區功能。遊戲開發者或動畫創作者可在本地環境中自動化生成動畫幀圖集並直接進行場景合成，無需依賴雲端服務，整個製作流程在單一工具內完成。
> _Codex-assisted local 2D animation spritesheet generator and scene compositing workspace._

📍 出處 / via: GitHub new-repo search

### 48. [Plaer1/junction](https://github.com/Plaer1/junction)
⭐ 514 · 🆕 new · TypeScript

> VS Code 側邊欄的 AI 聊天介面，專為連接本地執行的 AI 程式設計代理而設計。開發者無需離開 IDE 即可直接與本地模型對話協作，不依賴外部 API 費用，適合重視資料隱私或需要在離線環境中進行 AI 輔助開發的使用者。
> _VS Code chat sidebar for local AI coding agents_

📍 出處 / via: GitHub new-repo search

### 49. [fivetaku/fablize](https://github.com/fivetaku/fablize)
⭐ 511 · 🆕 new · Python

> fablize 是一款 Claude Code 外掛，旨在讓 Opus 模型在輔助開發時遵循 Fable 的行為模式——強制執行補全、佐證與驗證三個步驟作為標準流程。移植的功能僅保留實際透過 Fable 與 Opus 對比實驗後確認可轉移的部分，不做超出範疇的承諾。對於希望在不切換模型的情況下提升 AI 程式輔助可靠性的開發者，這是一個立基於實測的務實方案。
> _A Claude Code plugin that makes Opus behave like Fable — completion, evidence, and verification enforced as procedure. Ships only what a Fable-vs-Opus comparison proved transferable._

📍 出處 / via: GitHub new-repo search

### 50. [BishopFox/cloudfox](https://github.com/BishopFox/cloudfox)
⭐ 2,493 · 🔥 20/day · Go

> CloudFox 由知名資安公司 BishopFox 開發，專門解決雲端滲透測試中「情境感知」耗時的痛點——測試人員進入陌生的雲端環境後，往往需要大量手動操作才能摸清資源分布與潛在攻擊面。此工具自動化枚舉雲端服務、權限與配置，讓攻擊路徑的發現更迅速有系統。隨著企業大量遷移至雲端，CloudFox 持續在雲端安全社群中受到重視，成為紅隊演練的常用利器。
> _Automating situational awareness for cloud penetration tests._

📍 出處 / via: GitHub Trending
