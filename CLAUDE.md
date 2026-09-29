# CLAUDE.md

이 저장소에서 작업하는 에이전트가 따르는 규칙이다.
브랜치 이름·PR 제목 태그·리뷰 기준은 [`docs/BRANCHING.md`](docs/BRANCHING.md)를 따른다.

## 커밋은 PR로 올린다

`main`에 바로 커밋하지 않는다. 모든 변경은 **브랜치 → PR → merge commit** 순서로 올린다.

1. `main`에서 분기한다: `git switch -c <접두어>/<짧은-설명>`
   (접두어와 kebab 표기는 `docs/BRANCHING.md`의 표를 따른다)
2. 커밋 메시지 끝에 빈 줄을 두고 공동작성자 줄을 넣는다.

   ```
   Co-authored-by: icn0 <334413165+icn0@users.noreply.github.com>
   ```

   Claude 공동작성자 줄(`Co-Authored-By: Claude ...`)과 `Generated with Claude Code` 표기는 넣지 않는다.
3. `git push -u origin <브랜치>` → `gh pr create` → `gh pr merge --merge --delete-branch`
   - PR 제목은 `docs/BRANCHING.md`의 `[지표]`·`[수정]`·`[문서]`·`[코퍼스]` 태그 형식을 쓴다.
   - CI가 도는 변경이면 `gh pr checks --watch`로 초록색을 확인한 뒤 머지한다.
4. 머지는 반드시 **merge commit**(`--merge`)으로 한다. squash는 공동작성자 줄이 빠질 수 있어 쓰지 않는다.
5. 변경을 PR 하나에 몰아넣지 않는다. 의미 단위로 나눠 PR 여러 개로 올린다.

gh 기본 계정은 **kimjusnu**로 유지한다. icn0 토큰이 필요하면 그 명령에만
`GH_TOKEN=$(gh auth token -u icn0)`를 붙인다.
