#!/usr/bin/env python
from ban.commands.helpers import load_commands
from ban.commands import parser


def main():
    load_commands()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
