import sys

if len(sys.argv) > 2 and sys.argv[1] in ["-t", "--test"]:
    # Could be better with argparse
    import test.test_message as test

    match sys.argv[2]:
        case "c" | "client":
            test.send_message(sys.argv[3:])
    
        case "s" | "server":
            test.start_server()

        case "stop_server" | "ss":
            test.stop_server()
        
        case _:
            pass

    exit(0)

# ...