# Discord Bot Study - AI Agent Instructions

## Architecture Overview
This is a Discord bot for YC University notices and role management. Key components:
- **Bot Layer** (`bot/`): Discord client setup, commands, and event handling
- **Services** (`services/`): Background watchers for notices and roles using discord.py tasks
- **Crawler** (`crawler/`): HTML parsing with BeautifulSoup for university notice boards
- **UI** (`ui/`): Persistent Discord views for interactive role selection
- **Models** (`models/`): Simple dataclasses for data structures
- **Utils** (`utils/`): Thread-safe HTTP client with session reuse

## Key Patterns
- **State Persistence**: Use JSON files (`state.json`, `role_state.json`) for last processed IDs and message IDs. Load/save via helper functions in services.
- **Watcher Pattern**: Extend `discord.ext.tasks` for periodic background tasks. Start in `on_ready` event.
- **HTTP Requests**: Always use `utils.http_client.get()` for thread-safe requests with session reuse. Initialize with `init_http()` once.
- **Role Management**: Single grade role per user - remove conflicting roles before adding new one (see `GradeRoleView._apply_grade_role`).
- **Notice Parsing**: Parse HTML tables with BeautifulSoup, extract onclick attributes using regex (`ONCLICK_RE` in `crawler/notices.py`).
- **Persistent Views**: Register views with `bot.add_view()` for interactive components that survive restarts.

## Configuration
- Load secrets from `.env` via `python-dotenv`
- Hardcode Discord IDs (channels, roles) in `config.py` - update for new servers
- Check intervals and URLs defined in config

## Development Workflow
- Run with `python main.py` or `run.bat` (auto-restarts on changes via watchdog)
- Test commands in designated test channels (`TEST_CHANNEL_ID`)
- Debug: Check `state.json` for last processed notices, verify HTTP responses in crawler

## Code Style
- Use dataclasses for models
- Async/await for Discord operations
- Threading.Lock for shared resources (HTTP session)
- Import from relative modules (e.g., `from services.notice_watcher import create_school_notice_watcher`)

## Common Tasks
- Adding new notice sources: Create fetch function in `crawler/`, add watcher in `services/`, update config URLs/channels
- New UI components: Create view class in `ui/`, register in watcher `start()` method
- Role modifications: Update `ROLE_MAP` in `ui/grade_role_view.py` and config IDs