"""README parser for extracting structure and content."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from markdown_it import MarkdownIt
from markdown_it.token import Token


@dataclass
class ReadmeSection:
    """Represents a section of a README file."""

    title: str
    content: str
    level: int  # Heading level (1-6)
    parent_title: Optional[str] = None
    line_start: int = 0
    line_end: int = 0
    children: List["ReadmeSection"] = None

    def __post_init__(self) -> None:
        """Initialize children list if not provided."""
        if self.children is None:
            self.children = []


class Parser:
    """Parser for README.md files."""

    def __init__(self) -> None:
        """Initialize parser."""
        self.md = MarkdownIt()
        self._sections: List[ReadmeSection] = []
        self._current_section: Optional[ReadmeSection] = None
        self._section_stack: List[ReadmeSection] = []

    async def parse_file(self, file_path: str | Path) -> List[ReadmeSection]:
        """Parse a README file.

        Args:
            file_path: Path to README file

        Returns:
            List of README sections
        """
        file_path = Path(file_path)
        content = file_path.read_text(encoding="utf-8")
        return await self.parse_content(content)

    async def parse_content(self, content: str) -> List[ReadmeSection]:
        """Parse README content.

        Args:
            content: README content as string

        Returns:
            List of README sections
        """
        self._sections = []
        self._section_stack = []
        self._current_section = None

        tokens = self.md.parse(content)
        lines = content.split("\n")

        self._process_tokens(tokens, lines)

        # Close any remaining sections
        self._close_current_section(len(lines))

        return self._build_section_hierarchy()

    def _process_tokens(self, tokens: List[Token], lines: List[str]) -> None:
        """Process markdown tokens.

        Args:
            tokens: List of markdown tokens
            lines: Original content lines
        """
        i = 0
        while i < len(tokens):
            token = tokens[i]

            if token.type == "heading_open":
                # Get heading level
                level = int(token.tag[1])  # h1 -> 1, h2 -> 2, etc.

                # Get heading text from next token
                title = ""
                if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                    title = tokens[i + 1].content

                # Close previous section if needed
                if self._current_section:
                    self._close_current_section(token.map[0] if token.map else 0)

                # Create new section
                self._current_section = ReadmeSection(
                    title=title,
                    content="",
                    level=level,
                    line_start=token.map[0] if token.map else 0,
                )

                # Skip heading_close token
                i += 2

            elif token.type == "paragraph_open" or token.type == "blockquote_open":
                # Accumulate content for current section
                if self._current_section and i + 1 < len(tokens):
                    content_token = tokens[i + 1]
                    if content_token.type == "inline":
                        self._add_content(content_token.content, lines)

            elif token.type == "code_block" or token.type == "fence":
                # Add code blocks to content
                if self._current_section:
                    self._add_content(f"```\n{token.content}\n```", lines)

            elif token.type == "bullet_list_open" or token.type == "ordered_list_open":
                # Process list items
                list_content = self._extract_list_content(tokens, i)
                if self._current_section and list_content:
                    self._add_content(list_content, lines)

            i += 1

    def _extract_list_content(self, tokens: List[Token], start_idx: int) -> str:
        """Extract content from a list.

        Args:
            tokens: List of tokens
            start_idx: Starting index of list

        Returns:
            Formatted list content
        """
        content_lines = []
        i = start_idx + 1

        while i < len(tokens):
            token = tokens[i]

            if token.type in ("bullet_list_close", "ordered_list_close"):
                break

            if token.type == "list_item_open":
                # Find inline content in this list item
                j = i + 1
                while j < len(tokens) and tokens[j].type != "list_item_close":
                    if tokens[j].type == "inline":
                        content_lines.append(f"- {tokens[j].content}")
                    j += 1
                i = j

            i += 1

        return "\n".join(content_lines)

    def _add_content(self, content: str, lines: List[str]) -> None:
        """Add content to current section.

        Args:
            content: Content to add
            lines: Original content lines
        """
        if self._current_section:
            if self._current_section.content:
                self._current_section.content += "\n\n"
            self._current_section.content += content.strip()

    def _close_current_section(self, line_end: int) -> None:
        """Close current section and add to sections list.

        Args:
            line_end: Ending line number
        """
        if self._current_section:
            self._current_section.line_end = line_end
            self._sections.append(self._current_section)
            self._current_section = None

    def _build_section_hierarchy(self) -> List[ReadmeSection]:
        """Build hierarchical structure of sections.

        Returns:
            Root-level sections with children
        """
        if not self._sections:
            return []

        root_sections = []
        stack: List[ReadmeSection] = []

        for section in self._sections:
            # Pop sections from stack that are at same or higher level
            while stack and stack[-1].level >= section.level:
                stack.pop()

            # If stack is empty, this is a root section
            if not stack:
                root_sections.append(section)
            else:
                # Add as child of current parent
                parent = stack[-1]
                section.parent_title = parent.title
                parent.children.append(section)

            # Push current section to stack
            stack.append(section)

        return root_sections

    def flatten_sections(self, sections: List[ReadmeSection]) -> List[ReadmeSection]:
        """Flatten hierarchical sections into a list.

        Args:
            sections: Hierarchical sections

        Returns:
            Flattened list of sections
        """
        flat = []
        for section in sections:
            flat.append(section)
            if section.children:
                flat.extend(self.flatten_sections(section.children))
        return flat

    def get_section_by_title(
        self, sections: List[ReadmeSection], title: str
    ) -> Optional[ReadmeSection]:
        """Find a section by title.

        Args:
            sections: List of sections to search
            title: Section title to find

        Returns:
            Section if found, None otherwise
        """
        for section in sections:
            if section.title.lower() == title.lower():
                return section
            if section.children:
                found = self.get_section_by_title(section.children, title)
                if found:
                    return found
        return None

    def get_toc(self, sections: List[ReadmeSection], max_level: int = 3) -> str:
        """Generate table of contents.

        Args:
            sections: List of sections
            max_level: Maximum heading level to include

        Returns:
            Markdown table of contents
        """
        lines = ["# Table of Contents\n"]

        def process_section(section: ReadmeSection, indent: int = 0) -> None:
            """Process section recursively."""
            if section.level <= max_level:
                indent_str = "  " * indent
                lines.append(f"{indent_str}- [{section.title}](#{self._slugify(section.title)})")

                for child in section.children:
                    process_section(child, indent + 1)

        for section in sections:
            process_section(section)

        return "\n".join(lines)

    def _slugify(self, text: str) -> str:
        """Convert text to slug for markdown links.

        Args:
            text: Text to slugify

        Returns:
            Slugified text
        """
        return text.lower().replace(" ", "-").replace(".", "").replace(",", "")
