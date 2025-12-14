import logging
import sys

from core.config import config


# ANSI Color Codes for Terminal
class Colors:
    """ANSI color codes for colorful terminal output."""

    # Reset
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground Colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright Foreground Colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Background Colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"


# Map string log levels to logging constants
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


class ColorfulFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels."""

    # Color scheme for each log level
    LEVEL_COLORS = {
        logging.DEBUG: Colors.BRIGHT_CYAN,
        logging.INFO: Colors.BRIGHT_GREEN,
        logging.WARNING: Colors.BRIGHT_YELLOW,
        logging.ERROR: Colors.BRIGHT_RED,
        logging.CRITICAL: Colors.BOLD + Colors.BG_RED + Colors.WHITE,
    }

    # Icons for each log level
    LEVEL_ICONS = {
        logging.DEBUG: "🔍",
        logging.INFO: "ℹ️ ",
        logging.WARNING: "⚠️ ",
        logging.ERROR: "❌",
        logging.CRITICAL: "💥",
    }

    def __init__(self, fmt: str = None, datefmt: str = None, use_colors: bool = True):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with colors."""
        if not self.use_colors:
            return super().format(record)

        # Save original values
        original_levelname = record.levelname
        original_msg = record.msg

        # Get colors for this level
        level_color = self.LEVEL_COLORS.get(record.levelno, Colors.WHITE)
        level_icon = self.LEVEL_ICONS.get(record.levelno, "•")

        # Colorize level name with icon
        record.levelname = (
            f"{level_color}{level_icon}  {original_levelname}{Colors.RESET}"
        )

        # Colorize timestamp
        colored_time = f"{Colors.BRIGHT_BLACK}{self.formatTime(record, self.datefmt)}{Colors.RESET}"

        # Colorize filename and line number
        colored_location = (
            f"{Colors.CYAN}{record.filename}{Colors.RESET}"
            f"{Colors.BRIGHT_BLACK}:{Colors.RESET}"
            f"{Colors.BRIGHT_MAGENTA}{record.lineno}{Colors.RESET}"
        )

        # Create the formatted message
        formatted_msg = super().format(record)

        # Restore original values
        record.levelname = original_levelname
        record.msg = original_msg

        # Replace placeholders with colored versions
        formatted_msg = formatted_msg.replace(
            self.formatTime(record, self.datefmt), colored_time
        )
        formatted_msg = formatted_msg.replace(
            f"{record.filename}:{record.lineno}", colored_location
        )

        return formatted_msg


def setup_logging() -> logging.Logger:
    """
    Configure application logging with colorful output.

    Default log level is INFO. SQL logs only show when LOG_LEVEL=DEBUG.
    Colors are enabled by default for better readability.
    """
    log_level = LOG_LEVELS.get(config.LOG_LEVEL.upper(), logging.INFO)

    # Detect if colors should be used (disabled in non-TTY environments)
    use_colors = sys.stdout.isatty()

    # Create colorful formatter
    formatter = ColorfulFormatter(
        fmt="%(asctime)s │ %(levelname)-8s │ %(filename)s:%(lineno)d │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        use_colors=use_colors,
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)

    # Log startup message with colors
    if use_colors:
        startup_msg = (
            f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}"
            f"╔══════════════════════════════════════════════════════════════════════╗\n"
            f"║                                                                      ║\n"
            f"║  {Colors.BRIGHT_MAGENTA}███████╗{Colors.BRIGHT_CYAN}  ██╗  ██╗{Colors.BRIGHT_YELLOW} ██╗{Colors.BRIGHT_GREEN} ███████╗{Colors.BRIGHT_RED} ██╗{Colors.BRIGHT_CYAN}                  ║\n"
            f"║  {Colors.BRIGHT_MAGENTA}██╔════╝{Colors.BRIGHT_CYAN} ██║  ██║{Colors.BRIGHT_YELLOW} ██║{Colors.BRIGHT_GREEN} ██╔════╝{Colors.BRIGHT_RED} ██║{Colors.BRIGHT_CYAN}                  ║\n"
            f"║  {Colors.BRIGHT_MAGENTA}█████╗  {Colors.BRIGHT_CYAN} ███████║{Colors.BRIGHT_YELLOW} ██║{Colors.BRIGHT_GREEN} ███████╗{Colors.BRIGHT_RED} ██║{Colors.BRIGHT_CYAN}                  ║\n"
            f"║  {Colors.BRIGHT_MAGENTA}██╔══╝  {Colors.BRIGHT_CYAN} ╚════██║{Colors.BRIGHT_YELLOW} ██║{Colors.BRIGHT_GREEN} ╚════██║{Colors.BRIGHT_RED} ██║{Colors.BRIGHT_CYAN}                  ║\n"
            f"║  {Colors.BRIGHT_MAGENTA}██║     {Colors.BRIGHT_CYAN}      ██║{Colors.BRIGHT_YELLOW} ██║{Colors.BRIGHT_GREEN} ███████║{Colors.BRIGHT_RED} ██║{Colors.BRIGHT_CYAN}                  ║\n"
            f"║  {Colors.BRIGHT_MAGENTA}╚═╝     {Colors.BRIGHT_CYAN}      ╚═╝{Colors.BRIGHT_YELLOW} ╚═╝{Colors.BRIGHT_GREEN} ╚══════╝{Colors.BRIGHT_RED} ╚═╝{Colors.BRIGHT_CYAN}                  ║\n"
            f"║                                                                      ║\n"
            f"║           {Colors.BRIGHT_WHITE}💻 Developer: F4i5i {Colors.BRIGHT_CYAN}│ {Colors.BRIGHT_YELLOW}🎨 Colorful Logging v1.0{Colors.BRIGHT_CYAN}        ║\n"
            f"║                                                                      ║\n"
            f"║     🚀 CSF Backend - Colorful Logging Initialized Successfully      ║\n"
            f"║     {Colors.BRIGHT_GREEN}Log Level: {config.LOG_LEVEL.upper():<52}{Colors.BRIGHT_CYAN} ║\n"
            f"║                                                                      ║\n"
            f"╚══════════════════════════════════════════════════════════════════════╝"
            f"{Colors.RESET}\n"
        )
        print(startup_msg)

    # Third-party loggers - reduce noise
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("multipart").setLevel(logging.WARNING)

    # SQLAlchemy - only show SQL text at DEBUG level to avoid leaking PII in logs
    sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
    if log_level <= logging.DEBUG:
        sqlalchemy_logger.setLevel(logging.DEBUG)
        root_logger.info(
            f"{Colors.BRIGHT_YELLOW}🗄️  SQL logging enabled (DEBUG mode){Colors.RESET}"
        )
    else:
        sqlalchemy_logger.setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)
