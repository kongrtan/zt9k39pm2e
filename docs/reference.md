# 참조

작업 환경 설정과 자주 찾는 참고 사항을 모아 둔다.

---

## 1. 다른 PC의 VS Code에서 Mermaid 미리보기 설정

이 저장소의 문서는 Mermaid 그림을 많이 쓴다. VS Code 기본 Markdown 미리보기는 Mermaid를 그리지 못하므로, 아래 확장과 설정이 필요하다.

### 1.1 확장 설치

| 확장 | ID | 역할 |
|---|---|---|
| Markdown Preview Mermaid Support | `bierner.markdown-mermaid` | 미리보기에서 ` ```mermaid ` 블록을 그림으로 렌더링 |
| Markdown Preview GitHub Styling | `bierner.markdown-preview-github-styles` | 미리보기를 GitHub 스타일로 표시 |

**방법 A. 명령으로 설치** (VS Code의 `code` 명령이 PATH에 있을 때)

```bash
code --install-extension bierner.markdown-mermaid
code --install-extension bierner.markdown-preview-github-styles
```

**방법 B. VS Code 화면에서 설치**

1. `Ctrl+Shift+X` (확장 탭)
2. 검색창에 `bierner.markdown-mermaid` 입력 → **Install**
3. 검색창에 `bierner.markdown-preview-github-styles` 입력 → **Install**

**방법 C. 확장 마켓플레이스에 접속할 수 없을 때 (오프라인 설치)**

1. 인터넷이 되는 PC에서 `.vsix` 파일을 받는다.
   - https://marketplace.visualstudio.com/items?itemName=bierner.markdown-mermaid → **Download Extension**
   - https://marketplace.visualstudio.com/items?itemName=bierner.markdown-preview-github-styles → **Download Extension**
   - 또는 Open VSX: https://open-vsx.org/extension/bierner/markdown-mermaid , https://open-vsx.org/extension/bierner/markdown-preview-github-styles
2. 파일을 대상 PC로 옮긴 뒤 설치한다.

```bash
code --install-extension bierner.markdown-mermaid-<버전>.vsix
code --install-extension bierner.markdown-preview-github-styles-<버전>.vsix
```

또는 확장 탭 우측 상단 `...` → **Install from VSIX...** 에서 파일을 선택한다.

### 1.2 설정 (선택)

`.vscode/` 폴더는 Git에 올리지 않으므로 다른 PC에서는 직접 만든다. 저장소 루트에 아래 두 파일을 만든다.

**`.vscode/settings.json`**

```jsonc
{
  // Mermaid: VS Code가 다크 테마면 dark, 라이트면 default 테마로 그림
  "markdown-mermaid.darkModeTheme": "dark",
  "markdown-mermaid.lightModeTheme": "default",
  // GitHub 스타일 미리보기가 VS Code 테마를 따라감
  "markdown-preview-github-styles.colorTheme": "auto",
  // 미리보기 본문 글자 크기 (GitHub 기본값은 16)
  "markdown.preview.fontSize": 14,
  // 추가 CSS: 본문 글자 크기, 다크 모드에서 Mermaid 그림 뒤 회색 패널
  "markdown.styles": [".vscode/markdown-preview.css"]
}
```

**`.vscode/markdown-preview.css`**

```css
/* 본문 글자를 GitHub 기본값(16px)보다 2px 작게 */
body,
.markdown-body {
  font-size: 14px !important;
}

/* 다크 모드에서만 Mermaid 그림 뒤에 회색 패널 */
.vscode-dark .mermaid,
.vscode-high-contrast .mermaid {
  background: #474747;
  border: 1px solid #6e6e6e;
  border-radius: 6px;
  padding: 16px;
}
```

모든 프로젝트에 적용하려면 `settings.json` 내용을 사용자 설정(`Ctrl+Shift+P` → **Preferences: Open User Settings (JSON)**)에 넣는다. 이때 `markdown.styles`의 CSS 경로는 절대 경로로 쓴다.

### 1.3 사용

- 미리보기: `Ctrl+Shift+V`
- 옆 창에 미리보기: `Ctrl+K` 다음 `V`
- 확장을 설치하거나 설정을 바꾼 뒤 그림이 보이지 않으면, 미리보기를 닫았다가 다시 열거나 `Ctrl+Shift+P` → **Developer: Reload Window**를 실행한다.

### 1.4 참고

- VS Code 확장과 GitHub은 내장된 Mermaid 버전이 달라서 그림이 조금 다르게 보일 수 있다. 최종 확인은 GitHub 화면 기준으로 한다.
- GitHub 화면은 CSS를 바꿀 수 없다. 글자가 크게 느껴지면 브라우저에서 `Ctrl -`로 축소한다.
- 대안 확장: **Markdown Preview Enhanced** (`shd101wyy.markdown-preview-enhanced`). Mermaid, PlantUML, 목차, PDF 내보내기를 지원하며 자체 미리보기 창을 쓴다.
