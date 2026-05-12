from patterns import MaxExecTime, Recurring, WaitForEvent

def main():
    maxexectimeXML = MaxExecTime(200, "TaskA", "target1")
    recurringXML = Recurring("CheckID", "TaskB", 200, "target2")
    waitforeventXML = WaitForEvent("TaskID")
    print(maxexectimeXML)
    print(recurringXML)
    print(waitforeventXML)
    with open("maxexectime.xml", "w") as f:
        f.write(maxexectimeXML)
    with open("recurring.xml", "w") as f:
        f.write(recurringXML)
    with open("waitforevent.xml", "w") as f:
        f.write(waitforeventXML)

if __name__ == "__main__":
    main()