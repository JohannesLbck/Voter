from hashmap import hash_t
import httpx


def min_time_between(callback, ctime, activity, instance, args):
    print("reached")
    print(callback)
    print(ctime)
    print(activity)
    print(args)
    if activity == args["A"]:
        print("A branch")
        args["A_time"] = ctime 
        hash_t.delete(instance)
        hash_t.insert(instance, args)
        hash_t.save_disk("Constraints.json")
        ## return continue here
    elif activity == args["B"]:
        if args["A_time"] + args["time"] < time.time():
            if args["alternative"]:
                pass
                ## Execute alternative here
            else:
                pass
                ## Callback / wait here
        else:
            pass
            ## returne continue here
    else:
        pass
    pass
