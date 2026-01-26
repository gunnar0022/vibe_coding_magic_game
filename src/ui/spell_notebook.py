"""
Spell Notebook - In-game reference book for learned spells/symbols.
Features index with keyword search, spell pages with descriptions,
and player note pages.
"""
import pygame


# Default spell data - will eventually come from JSON
DEFAULT_SPELL_DATA = {
    "fire": {
        "character": "\u706b",
        "name": "Fire",
        "keywords": ["fire", "heat", "burn", "elemental", "offensive"],
        "description": (
            "The symbol of Fire channels raw thermal energy. "
            "When cast, it releases a burst of flame that can ignite "
            "flammable objects and apply burning status to targets.\n\n"
            "Mechanical Effects:\n"
            "- Applies 'burning' status to flammable targets\n"
            "- Burning deals damage over time\n"
            "- Can spread to nearby flammable objects\n"
            "- Extinguished by water"
        ),
    },
    "water": {
        "character": "\u6c34",
        "name": "Water",
        "keywords": ["water", "liquid", "extinguish", "elemental", "utility"],
        "description": (
            "The symbol of Water summons forth a flow of pure water. "
            "It can extinguish flames and applies the wet status to targets.\n\n"
            "Mechanical Effects:\n"
            "- Extinguishes burning status\n"
            "- Applies 'wet' status to targets\n"
            "- Wet targets take increased lightning damage\n"
            "- Can interact with environmental water"
        ),
    },
    "force": {
        "character": "\u529b",
        "name": "Force",
        "keywords": ["force", "push", "physical", "motion", "utility"],
        "description": (
            "The symbol of Force manifests raw kinetic energy. "
            "It pushes objects and creatures away from the caster.\n\n"
            "Mechanical Effects:\n"
            "- Pushes movable objects (like rocks) one tile\n"
            "- Direction based on casting angle\n"
            "- Blocked by immovable objects or walls\n"
            "- Can be used to solve puzzles"
        ),
    },
    "motion": {
        "character": "\u52d5",
        "name": "Motion",
        "keywords": ["motion", "movement", "speed", "physical", "utility"],
        "description": (
            "The symbol of Motion embodies the essence of movement itself. "
            "It can accelerate objects or grant swiftness.\n\n"
            "Mechanical Effects:\n"
            "- Similar to Force but focused on velocity\n"
            "- Can affect movement speed\n"
            "- Combines well with other elements\n"
            "- Useful for traversal puzzles"
        ),
    },
}


class SpellNotebook:
    """
    A book-style UI for viewing learned spells and taking notes.
    Does not pause the game - time continues while viewing.
    """

    # Layout constants
    SPELLS_PER_INDEX_PAGE = 8  # How many spells fit on one index page

    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Notebook state
        self.is_open = False
        self.current_page = "index"  # "index", "index_2", or spell_id
        self.index_page_num = 0  # For multiple index pages
        self.spell_subpage = 0  # 0=main spread, 1-3=extra note pages

        # Known spells (list of spell IDs in order learned)
        self.known_spells = []

        # Player data per spell
        self.spell_player_data = {}  # spell_id -> {keywords: [], notes: ["", "", ""]}

        # Search state
        self.search_text = ""
        self.search_active = False

        # Text input state (for notes)
        self.editing_notes = False
        self.current_note_page = 0  # Which note page being edited (0-2)
        self.cursor_pos = 0

        # Visual properties
        self.book_width = 700
        self.book_height = 500
        self.book_x = (screen_width - self.book_width) // 2
        self.book_y = (screen_height - self.book_height) // 2
        self.page_width = self.book_width // 2 - 40
        self.margin = 30

        # Colors (parchment/book theme)
        self.bg_color = (45, 35, 30)  # Dark leather binding
        self.page_color = (245, 235, 220)  # Parchment
        self.text_color = (40, 30, 25)  # Dark ink
        self.accent_color = (120, 80, 50)  # Brown accent
        self.highlight_color = (255, 240, 150)  # Search highlight
        self.keyword_bg = (230, 220, 200)  # Keyword tag background

        # Fonts
        self.font = None
        self.title_font = None
        self.symbol_font = None
        self.small_font = None

        # Clickable regions (populated during render)
        self.clickable_spells = []  # [(rect, spell_id), ...]
        self.nav_buttons = {}  # name -> rect

        # Note character limits
        self.chars_per_note_page = 400

    def _init_fonts(self):
        """Initialize fonts."""
        if self.font is None:
            pygame.font.init()
            self.font = pygame.font.Font(None, 24)
            self.title_font = pygame.font.Font(None, 36)
            self.small_font = pygame.font.Font(None, 20)

            # Try to get a CJK-capable font for symbols
            cjk_fonts = ["microsoftyahei", "yugothic", "msgothic", "simsun"]
            self.symbol_font = None
            for font_name in cjk_fonts:
                try:
                    self.symbol_font = pygame.font.SysFont(font_name, 42)
                    test = self.symbol_font.render("\u706b", True, (0, 0, 0))
                    if test.get_width() > 5:
                        break
                except:
                    continue
            if self.symbol_font is None:
                self.symbol_font = pygame.font.Font(None, 42)

    def open(self):
        """Open the notebook."""
        self._init_fonts()
        self.is_open = True
        self.current_page = "index"
        self.index_page_num = 0
        self.spell_subpage = 0
        self.search_text = ""
        self.search_active = False
        self.editing_notes = False

    def close(self):
        """Close the notebook."""
        self.is_open = False
        self.editing_notes = False
        self.search_active = False

    def learn_spell(self, spell_id):
        """Add a spell to the known spells list."""
        if spell_id not in self.known_spells and spell_id in DEFAULT_SPELL_DATA:
            self.known_spells.append(spell_id)
            # Initialize player data for this spell
            self.spell_player_data[spell_id] = {
                "keywords": [],  # Player-added keywords
                "notes": ["", "", ""],  # Up to 3 pages of notes
            }

    def get_spell_data(self, spell_id):
        """Get combined spell data (default + player)."""
        if spell_id not in DEFAULT_SPELL_DATA:
            return None

        default = DEFAULT_SPELL_DATA[spell_id]
        player = self.spell_player_data.get(spell_id, {"keywords": [], "notes": ["", "", ""]})

        return {
            "id": spell_id,
            "character": default["character"],
            "name": default["name"],
            "keywords": default["keywords"] + player["keywords"],
            "default_keywords": default["keywords"],
            "player_keywords": player["keywords"],
            "description": default["description"],
            "notes": player["notes"],
        }

    def add_player_keyword(self, spell_id, keyword):
        """Add a player-defined keyword to a spell."""
        if spell_id in self.spell_player_data:
            keyword = keyword.strip().lower()
            if keyword and keyword not in self.spell_player_data[spell_id]["keywords"]:
                self.spell_player_data[spell_id]["keywords"].append(keyword)

    def set_note(self, spell_id, page_index, text):
        """Set note text for a spell's note page."""
        if spell_id in self.spell_player_data:
            if 0 <= page_index < 3:
                # Enforce character limit
                self.spell_player_data[spell_id]["notes"][page_index] = text[:self.chars_per_note_page]

    def _get_filtered_spells(self):
        """Get list of spells filtered by search text."""
        if not self.search_text:
            return [(sid, False) for sid in self.known_spells]

        search_lower = self.search_text.lower()
        results = []

        for spell_id in self.known_spells:
            data = self.get_spell_data(spell_id)
            if data is None:
                continue

            # Check if search matches character, name, or keywords
            matches = False
            if search_lower in data["character"]:
                matches = True
            elif search_lower in data["name"].lower():
                matches = True
            else:
                for kw in data["keywords"]:
                    if search_lower in kw.lower():
                        matches = True
                        break

            results.append((spell_id, matches))

        return results

    def handle_input(self, input_handler, events):
        """Handle input for the notebook. Returns True if notebook consumed the input."""
        if not self.is_open:
            return False

        mouse_x, mouse_y = input_handler.get_mouse_position()

        # Handle text input for search or notes
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.search_active:
                    self._handle_search_input(event)
                elif self.editing_notes:
                    self._handle_note_input(event)

        # ESC closes notebook or exits edit mode
        if input_handler.cancel:
            if self.editing_notes:
                self.editing_notes = False
            elif self.search_active:
                self.search_active = False
                self.search_text = ""
            else:
                self.close()
            return True

        # Mouse click handling
        if input_handler.mouse_clicked:
            return self._handle_click(mouse_x, mouse_y)

        # Keyboard navigation
        if not self.search_active and not self.editing_notes:
            if input_handler.was_key_pressed(pygame.K_a) or input_handler.was_key_pressed(pygame.K_LEFT):
                self._prev_page()
                return True
            if input_handler.was_key_pressed(pygame.K_d) or input_handler.was_key_pressed(pygame.K_RIGHT):
                self._next_page()
                return True

        return True  # Notebook is open, consume input

    def _handle_search_input(self, event):
        """Handle keyboard input for search."""
        if event.key == pygame.K_RETURN:
            self.search_active = False
        elif event.key == pygame.K_BACKSPACE:
            self.search_text = self.search_text[:-1]
        elif event.key == pygame.K_ESCAPE:
            self.search_active = False
            self.search_text = ""
        elif event.unicode and len(self.search_text) < 20:
            self.search_text += event.unicode

    def _handle_note_input(self, event):
        """Handle keyboard input for note editing."""
        spell_id = self.current_page
        if spell_id == "index" or spell_id not in self.spell_player_data:
            return

        notes = self.spell_player_data[spell_id]["notes"]
        current_text = notes[self.current_note_page]

        if event.key == pygame.K_RETURN:
            # Add newline
            if len(current_text) < self.chars_per_note_page - 1:
                current_text = current_text[:self.cursor_pos] + "\n" + current_text[self.cursor_pos:]
                self.cursor_pos += 1
        elif event.key == pygame.K_BACKSPACE:
            if self.cursor_pos > 0:
                current_text = current_text[:self.cursor_pos-1] + current_text[self.cursor_pos:]
                self.cursor_pos -= 1
        elif event.key == pygame.K_DELETE:
            current_text = current_text[:self.cursor_pos] + current_text[self.cursor_pos+1:]
        elif event.key == pygame.K_LEFT:
            self.cursor_pos = max(0, self.cursor_pos - 1)
        elif event.key == pygame.K_RIGHT:
            self.cursor_pos = min(len(current_text), self.cursor_pos + 1)
        elif event.key == pygame.K_HOME:
            self.cursor_pos = 0
        elif event.key == pygame.K_END:
            self.cursor_pos = len(current_text)
        elif event.unicode and len(current_text) < self.chars_per_note_page:
            current_text = current_text[:self.cursor_pos] + event.unicode + current_text[self.cursor_pos:]
            self.cursor_pos += 1

        notes[self.current_note_page] = current_text

    def _handle_click(self, mouse_x, mouse_y):
        """Handle mouse click."""
        # Check navigation buttons
        for name, rect in self.nav_buttons.items():
            if rect.collidepoint(mouse_x, mouse_y):
                if name == "prev":
                    self._prev_page()
                elif name == "next":
                    self._next_page()
                elif name == "index":
                    self.current_page = "index"
                    self.index_page_num = 0
                    self.spell_subpage = 0
                elif name == "search":
                    self.search_active = True
                elif name == "edit_notes":
                    self.editing_notes = True
                    self.current_note_page = max(0, self.spell_subpage - 1) if self.spell_subpage > 0 else 0
                    spell_id = self.current_page
                    if spell_id in self.spell_player_data:
                        self.cursor_pos = len(self.spell_player_data[spell_id]["notes"][self.current_note_page])
                elif name == "add_note_page":
                    # Go to next note page
                    self.spell_subpage = min(3, self.spell_subpage + 1)
                elif name == "close":
                    self.close()
                return True

        # Check clickable spells in index
        for rect, spell_id in self.clickable_spells:
            if rect.collidepoint(mouse_x, mouse_y):
                self.current_page = spell_id
                self.spell_subpage = 0
                self.editing_notes = False
                return True

        # Click on note area to start editing
        if self.current_page != "index" and self.current_page in self.known_spells:
            note_area = self.nav_buttons.get("note_area")
            if note_area and note_area.collidepoint(mouse_x, mouse_y):
                self.editing_notes = True
                self.current_note_page = max(0, self.spell_subpage - 1) if self.spell_subpage > 0 else 0
                spell_id = self.current_page
                if spell_id in self.spell_player_data:
                    self.cursor_pos = len(self.spell_player_data[spell_id]["notes"][self.current_note_page])
                return True

        return True

    def _prev_page(self):
        """Go to previous page."""
        if self.current_page == "index":
            if self.index_page_num > 0:
                self.index_page_num -= 1
        else:
            if self.spell_subpage > 0:
                self.spell_subpage -= 1
            else:
                # Go to previous spell or index
                if self.current_page in self.known_spells:
                    idx = self.known_spells.index(self.current_page)
                    if idx > 0:
                        self.current_page = self.known_spells[idx - 1]
                        self.spell_subpage = 0
                    else:
                        self.current_page = "index"

    def _next_page(self):
        """Go to next page."""
        if self.current_page == "index":
            # Check if there are more index pages
            total_index_pages = (len(self.known_spells) + self.SPELLS_PER_INDEX_PAGE - 1) // self.SPELLS_PER_INDEX_PAGE
            if self.index_page_num < total_index_pages - 1:
                self.index_page_num += 1
            elif self.known_spells:
                # Go to first spell
                self.current_page = self.known_spells[0]
                self.spell_subpage = 0
        else:
            # Check if there are extra note pages with content
            spell_data = self.spell_player_data.get(self.current_page, {})
            notes = spell_data.get("notes", ["", "", ""])

            # Can go to subpage 1-3 if there's content or we're already past 0
            if self.spell_subpage == 0:
                # Main spread -> first note page (if has content or user wants to add)
                if notes[0]:
                    self.spell_subpage = 1
                else:
                    # Go to next spell
                    self._goto_next_spell()
            elif self.spell_subpage < 3 and notes[self.spell_subpage - 1]:
                # Has content on current extra page, can go to next
                self.spell_subpage += 1
            else:
                self._goto_next_spell()

    def _goto_next_spell(self):
        """Go to the next spell in the list."""
        if self.current_page in self.known_spells:
            idx = self.known_spells.index(self.current_page)
            if idx < len(self.known_spells) - 1:
                self.current_page = self.known_spells[idx + 1]
                self.spell_subpage = 0
            # else: stay on last spell

    def render(self, screen):
        """Render the notebook."""
        if not self.is_open:
            return

        self._init_fonts()
        self.clickable_spells = []
        self.nav_buttons = {}

        # Draw book background (binding)
        book_rect = pygame.Rect(self.book_x - 10, self.book_y - 10,
                                self.book_width + 20, self.book_height + 20)
        pygame.draw.rect(screen, self.bg_color, book_rect, border_radius=5)

        # Draw pages
        left_page = pygame.Rect(self.book_x, self.book_y,
                                self.book_width // 2, self.book_height)
        right_page = pygame.Rect(self.book_x + self.book_width // 2, self.book_y,
                                 self.book_width // 2, self.book_height)

        pygame.draw.rect(screen, self.page_color, left_page)
        pygame.draw.rect(screen, self.page_color, right_page)

        # Center binding line
        pygame.draw.line(screen, self.accent_color,
                         (self.book_x + self.book_width // 2, self.book_y),
                         (self.book_x + self.book_width // 2, self.book_y + self.book_height), 3)

        # Render content based on current page
        if self.current_page == "index":
            self._render_index(screen, left_page, right_page)
        else:
            self._render_spell_page(screen, left_page, right_page)

        # Close button
        close_rect = pygame.Rect(book_rect.right - 30, book_rect.top + 5, 25, 25)
        pygame.draw.rect(screen, (150, 100, 100), close_rect, border_radius=3)
        x_surf = self.font.render("X", True, (255, 255, 255))
        screen.blit(x_surf, x_surf.get_rect(center=close_rect.center))
        self.nav_buttons["close"] = close_rect

    def _render_index(self, screen, left_page, right_page):
        """Render the index page(s)."""
        # Title on left page
        title = self.title_font.render("~ Spell Index ~", True, self.text_color)
        screen.blit(title, (left_page.centerx - title.get_width() // 2, left_page.top + 20))

        # Search box
        search_y = left_page.top + 60
        search_rect = pygame.Rect(left_page.left + 20, search_y, left_page.width - 40, 30)
        pygame.draw.rect(screen, (255, 255, 255), search_rect, border_radius=3)
        pygame.draw.rect(screen, self.accent_color, search_rect, 2, border_radius=3)

        search_label = self.small_font.render("Search:", True, self.text_color)
        screen.blit(search_label, (search_rect.left + 5, search_rect.centery - search_label.get_height() // 2))

        search_text_surf = self.font.render(self.search_text or "click to search...", True,
                                            self.text_color if self.search_text else (150, 140, 130))
        screen.blit(search_text_surf, (search_rect.left + 60, search_rect.centery - search_text_surf.get_height() // 2))

        if self.search_active:
            # Draw cursor
            cursor_x = search_rect.left + 60 + self.font.size(self.search_text)[0]
            pygame.draw.line(screen, self.text_color, (cursor_x, search_rect.top + 5),
                             (cursor_x, search_rect.bottom - 5), 2)

        self.nav_buttons["search"] = search_rect

        # Get filtered spells
        filtered = self._get_filtered_spells()

        # Calculate which spells to show on this index page
        start_idx = self.index_page_num * self.SPELLS_PER_INDEX_PAGE
        end_idx = start_idx + self.SPELLS_PER_INDEX_PAGE
        page_spells = filtered[start_idx:end_idx]

        # Split between left and right pages
        left_spells = page_spells[:4]
        right_spells = page_spells[4:8]

        # Render spell entries
        self._render_index_entries(screen, left_page, left_spells, start_y=100)
        self._render_index_entries(screen, right_page, right_spells, start_y=40)

        # Page number
        total_pages = max(1, (len(self.known_spells) + self.SPELLS_PER_INDEX_PAGE - 1) // self.SPELLS_PER_INDEX_PAGE)
        page_text = f"Index {self.index_page_num + 1}/{total_pages}"
        page_surf = self.small_font.render(page_text, True, self.text_color)
        screen.blit(page_surf, (right_page.right - page_surf.get_width() - 20, right_page.bottom - 30))

        # Navigation hint
        nav_hint = self.small_font.render("A/D or Click to navigate", True, (120, 110, 100))
        screen.blit(nav_hint, (left_page.left + 20, left_page.bottom - 30))

    def _render_index_entries(self, screen, page_rect, spells, start_y):
        """Render spell entries on an index page."""
        y = page_rect.top + start_y

        for spell_id, matches_search in spells:
            data = self.get_spell_data(spell_id)
            if data is None:
                continue

            entry_rect = pygame.Rect(page_rect.left + 15, y, page_rect.width - 30, 90)

            # Highlight if matches search
            if self.search_text and matches_search:
                pygame.draw.rect(screen, self.highlight_color, entry_rect, border_radius=5)
            elif self.search_text and not matches_search:
                # Dim non-matching entries
                dim_surf = pygame.Surface((entry_rect.width, entry_rect.height), pygame.SRCALPHA)
                dim_surf.fill((245, 235, 220, 180))
                screen.blit(dim_surf, entry_rect.topleft)

            # Symbol
            symbol_surf = self.symbol_font.render(data["character"], True, self.text_color)
            screen.blit(symbol_surf, (entry_rect.left + 10, entry_rect.top + 5))

            # Page number (simulated)
            spell_idx = self.known_spells.index(spell_id) if spell_id in self.known_spells else 0
            page_num = f"p.{spell_idx + 1}"
            page_surf = self.small_font.render(page_num, True, self.accent_color)
            screen.blit(page_surf, (entry_rect.right - page_surf.get_width() - 10, entry_rect.top + 10))

            # Keywords (first 3)
            kw_y = entry_rect.top + 50
            kw_x = entry_rect.left + 10
            for i, kw in enumerate(data["keywords"][:3]):
                kw_surf = self.small_font.render(kw, True, self.text_color)
                kw_rect = pygame.Rect(kw_x, kw_y, kw_surf.get_width() + 10, kw_surf.get_height() + 4)
                pygame.draw.rect(screen, self.keyword_bg, kw_rect, border_radius=3)
                screen.blit(kw_surf, (kw_x + 5, kw_y + 2))
                kw_x += kw_rect.width + 5
                if kw_x > entry_rect.right - 50:
                    break

            # Divider line
            pygame.draw.line(screen, self.accent_color,
                             (entry_rect.left, entry_rect.bottom - 2),
                             (entry_rect.right, entry_rect.bottom - 2), 1)

            # Store clickable region
            self.clickable_spells.append((entry_rect, spell_id))

            y += 95

    def _render_spell_page(self, screen, left_page, right_page):
        """Render a spell's pages."""
        spell_data = self.get_spell_data(self.current_page)
        if spell_data is None:
            return

        if self.spell_subpage == 0:
            # Main spread: left = info, right = notes
            self._render_spell_info(screen, left_page, spell_data)
            self._render_spell_notes(screen, right_page, spell_data, note_page=0)
        else:
            # Extra note pages (full spread for notes)
            note_idx = self.spell_subpage - 1
            self._render_extra_notes(screen, left_page, right_page, spell_data, note_idx)

        # Navigation buttons
        self._render_spell_nav(screen, left_page, right_page, spell_data)

    def _render_spell_info(self, screen, page_rect, spell_data):
        """Render the spell information page (left side)."""
        x = page_rect.left + self.margin
        y = page_rect.top + 20

        # Symbol and name
        symbol_surf = self.symbol_font.render(spell_data["character"], True, self.text_color)
        screen.blit(symbol_surf, (x, y))

        name_surf = self.title_font.render(spell_data["name"], True, self.text_color)
        screen.blit(name_surf, (x + 60, y + 5))

        y += 55

        # Divider
        pygame.draw.line(screen, self.accent_color, (x, y), (page_rect.right - self.margin, y), 2)
        y += 15

        # Keywords section
        kw_label = self.small_font.render("Keywords:", True, self.accent_color)
        screen.blit(kw_label, (x, y))
        y += 20

        # Render keywords in rows
        kw_x = x
        for kw in spell_data["keywords"]:
            is_player_kw = kw in spell_data["player_keywords"]
            kw_surf = self.small_font.render(kw, True, self.text_color)
            kw_rect = pygame.Rect(kw_x, y, kw_surf.get_width() + 10, kw_surf.get_height() + 4)

            if kw_x + kw_rect.width > page_rect.right - self.margin:
                kw_x = x
                y += 22
                kw_rect.left = kw_x
                kw_rect.top = y

            bg_color = (200, 220, 200) if is_player_kw else self.keyword_bg
            pygame.draw.rect(screen, bg_color, kw_rect, border_radius=3)
            screen.blit(kw_surf, (kw_x + 5, kw_rect.top + 2))
            kw_x += kw_rect.width + 5

        y += 35

        # Description
        desc_label = self.small_font.render("Description:", True, self.accent_color)
        screen.blit(desc_label, (x, y))
        y += 20

        # Word wrap description
        self._render_wrapped_text(screen, spell_data["description"], x, y,
                                  page_rect.width - self.margin * 2, self.font, self.text_color)

    def _render_spell_notes(self, screen, page_rect, spell_data, note_page):
        """Render the notes page (right side of main spread)."""
        x = page_rect.left + self.margin
        y = page_rect.top + 20

        # Header
        header = self.title_font.render("Notes", True, self.text_color)
        screen.blit(header, (x, y))
        y += 40

        # Divider
        pygame.draw.line(screen, self.accent_color, (x, y), (page_rect.right - self.margin, y), 2)
        y += 15

        # Note area
        note_rect = pygame.Rect(x, y, page_rect.width - self.margin * 2, page_rect.height - y - 60)
        pygame.draw.rect(screen, (255, 255, 250), note_rect, border_radius=3)
        pygame.draw.rect(screen, self.accent_color, note_rect, 1, border_radius=3)

        self.nav_buttons["note_area"] = note_rect

        # Render note text
        notes = spell_data["notes"]
        note_text = notes[note_page] if note_page < len(notes) else ""

        if note_text or self.editing_notes:
            self._render_wrapped_text(screen, note_text or "Click to add notes...",
                                      note_rect.left + 10, note_rect.top + 10,
                                      note_rect.width - 20, self.font,
                                      self.text_color if note_text else (150, 140, 130),
                                      cursor_pos=self.cursor_pos if self.editing_notes else -1)
        else:
            hint = self.font.render("Click to add notes...", True, (150, 140, 130))
            screen.blit(hint, (note_rect.left + 10, note_rect.top + 10))

        # Edit indicator
        if self.editing_notes:
            edit_surf = self.small_font.render("[Editing - ESC to finish]", True, (100, 150, 100))
            screen.blit(edit_surf, (note_rect.left, note_rect.bottom + 5))

        # "Need more space?" button if notes have content
        if notes[0]:
            more_rect = pygame.Rect(page_rect.right - 120, page_rect.bottom - 35, 100, 25)
            pygame.draw.rect(screen, self.keyword_bg, more_rect, border_radius=3)
            more_surf = self.small_font.render("More pages...", True, self.text_color)
            screen.blit(more_surf, more_surf.get_rect(center=more_rect.center))
            self.nav_buttons["add_note_page"] = more_rect

    def _render_extra_notes(self, screen, left_page, right_page, spell_data, note_idx):
        """Render extra note pages (full spread)."""
        # Left page - continuation of notes
        x = left_page.left + self.margin
        y = left_page.top + 20

        header = self.title_font.render(f"{spell_data['name']} - Notes (cont.)", True, self.text_color)
        screen.blit(header, (x, y))
        y += 40

        # Note area on left
        note_rect = pygame.Rect(x, y, left_page.width - self.margin * 2, left_page.height - y - 40)
        pygame.draw.rect(screen, (255, 255, 250), note_rect, border_radius=3)
        pygame.draw.rect(screen, self.accent_color, note_rect, 1, border_radius=3)

        notes = spell_data["notes"]
        note_text = notes[note_idx] if note_idx < len(notes) else ""

        self._render_wrapped_text(screen, note_text or "Continue your notes here...",
                                  note_rect.left + 10, note_rect.top + 10,
                                  note_rect.width - 20, self.font,
                                  self.text_color if note_text else (150, 140, 130),
                                  cursor_pos=self.cursor_pos if self.editing_notes else -1)

        self.nav_buttons["note_area"] = note_rect

        # Right page - next note page or empty
        if note_idx + 1 < 3:
            x2 = right_page.left + self.margin
            y2 = right_page.top + 20

            header2 = self.small_font.render(f"Notes page {note_idx + 3}", True, self.accent_color)
            screen.blit(header2, (x2, y2))
            y2 += 30

            note_rect2 = pygame.Rect(x2, y2, right_page.width - self.margin * 2, right_page.height - y2 - 40)
            pygame.draw.rect(screen, (255, 255, 250), note_rect2, border_radius=3)
            pygame.draw.rect(screen, self.accent_color, note_rect2, 1, border_radius=3)

            next_note = notes[note_idx + 1] if note_idx + 1 < len(notes) else ""
            hint = self.font.render(next_note or "(Next page)", True,
                                    self.text_color if next_note else (180, 170, 160))
            screen.blit(hint, (note_rect2.left + 10, note_rect2.top + 10))

    def _render_spell_nav(self, screen, left_page, right_page, spell_data):
        """Render navigation elements for spell pages."""
        # Back to index button
        idx_rect = pygame.Rect(left_page.left + 15, left_page.bottom - 35, 80, 25)
        pygame.draw.rect(screen, self.keyword_bg, idx_rect, border_radius=3)
        idx_surf = self.small_font.render("< Index", True, self.text_color)
        screen.blit(idx_surf, idx_surf.get_rect(center=idx_rect.center))
        self.nav_buttons["index"] = idx_rect

        # Page indicator
        spell_idx = self.known_spells.index(self.current_page) + 1 if self.current_page in self.known_spells else 1
        page_text = f"Spell {spell_idx}/{len(self.known_spells)}"
        if self.spell_subpage > 0:
            page_text += f" (notes {self.spell_subpage})"
        page_surf = self.small_font.render(page_text, True, self.text_color)
        screen.blit(page_surf, (right_page.right - page_surf.get_width() - 20, right_page.bottom - 30))

        # Prev/Next arrows
        prev_rect = pygame.Rect(left_page.left + 15, left_page.top + left_page.height // 2 - 15, 30, 30)
        next_rect = pygame.Rect(right_page.right - 45, right_page.top + right_page.height // 2 - 15, 30, 30)

        pygame.draw.rect(screen, self.keyword_bg, prev_rect, border_radius=3)
        pygame.draw.rect(screen, self.keyword_bg, next_rect, border_radius=3)

        prev_surf = self.font.render("<", True, self.text_color)
        next_surf = self.font.render(">", True, self.text_color)
        screen.blit(prev_surf, prev_surf.get_rect(center=prev_rect.center))
        screen.blit(next_surf, next_surf.get_rect(center=next_rect.center))

        self.nav_buttons["prev"] = prev_rect
        self.nav_buttons["next"] = next_rect

    def _render_wrapped_text(self, screen, text, x, y, max_width, font, color, cursor_pos=-1):
        """Render text with word wrapping."""
        words = text.replace('\n', ' \n ').split(' ')
        lines = []
        current_line = ""
        char_count = 0
        cursor_line = -1
        cursor_x_offset = 0

        for word in words:
            if word == '\n':
                lines.append(current_line)
                if cursor_pos >= 0 and cursor_line < 0:
                    if char_count <= cursor_pos <= char_count + 1:
                        cursor_line = len(lines) - 1
                        cursor_x_offset = font.size(current_line)[0]
                char_count += 1
                current_line = ""
                continue

            test_line = current_line + (" " if current_line else "") + word
            if font.size(test_line)[0] <= max_width:
                if cursor_pos >= 0 and cursor_line < 0:
                    old_len = len(current_line)
                    if char_count + old_len < cursor_pos <= char_count + len(test_line):
                        cursor_line = len(lines)
                        cursor_x_offset = font.size(test_line[:cursor_pos - char_count])[0]
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                    if cursor_pos >= 0 and cursor_line < 0 and char_count <= cursor_pos <= char_count + len(current_line):
                        cursor_line = len(lines) - 1
                        cursor_x_offset = font.size(current_line[:cursor_pos - char_count])[0]
                    char_count += len(current_line) + 1
                current_line = word

        if current_line:
            lines.append(current_line)
            if cursor_pos >= 0 and cursor_line < 0:
                cursor_line = len(lines) - 1
                cursor_x_offset = font.size(current_line[:cursor_pos - char_count])[0]

        # Render lines
        line_height = font.get_linesize()
        for i, line in enumerate(lines):
            line_surf = font.render(line, True, color)
            screen.blit(line_surf, (x, y + i * line_height))

        # Render cursor
        if cursor_pos >= 0 and cursor_line >= 0:
            cursor_y = y + cursor_line * line_height
            pygame.draw.line(screen, self.text_color,
                             (x + cursor_x_offset, cursor_y),
                             (x + cursor_x_offset, cursor_y + line_height), 2)

    def serialize(self):
        """Serialize notebook data for saving."""
        return {
            "known_spells": self.known_spells,
            "spell_player_data": self.spell_player_data,
        }

    def deserialize(self, data):
        """Load notebook data from save."""
        self.known_spells = data.get("known_spells", [])
        self.spell_player_data = data.get("spell_player_data", {})

        # Ensure all known spells have player data
        for spell_id in self.known_spells:
            if spell_id not in self.spell_player_data:
                self.spell_player_data[spell_id] = {
                    "keywords": [],
                    "notes": ["", "", ""],
                }
