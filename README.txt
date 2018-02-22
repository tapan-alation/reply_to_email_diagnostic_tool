1. copy the script onto Alation chroot and move to /opt/alation/django/rosemeta/one_off_scripts director
   For example: 
	scp process_reply_to_emails.py $ALATION_IP:
        ssh $ALATION_IP
        cp process_reply_to_emails.py /data/tmp     // your path to data folder may be different
        sudo service alation shell
  	sudo su alation
	cd /opt/alation/django/rosemeta/one_off_scripts
  	cp /tmp/process_reply_to_emails.py .
	
2. Script can be run as follows
   python process_reply_to_emails.py | tee /tmp/process_reply_to_emails_output.$(date +%Y%m%d_%H%M%S).log

   By default, the script will check emails up to 5 times with delay of 5 seconds between each check.
   To change both these numbers, following options can be used:
   --check_count <num_of_times_to_check_here> --check_freq <num_of_seconds_to_delay_here>

   Ex: python process_reply_to_emails.py --check_count 10 --check_freq 3 | tee /tmp/process_reply_to_emails_output.$(date +%Y%m%d_%H%M%S).log

3. Process for using the script to debug Alation reply-to email functionality:
   a. Execute the script using the syntax described in step 2. 

      Note: By default Alation checks mail every 3 minutes, so it is possible that some mail may get processed by Alation backend vs this script. As long as the "check_freq" is set to small amount (few seconds perhaps), the script will usually be the one who consumes the email and not the Alation backend. 

   b. (Optional: This step is only needed if you don't already have an Alation mention mail you can reply to)
      Create a conversation in Alation. Have another user post a reply on that conversation with a mention to your Alation user, and wait till you receive the mention email

   c. Reply to a relevant email (you can reply indefinitely, so feel free to reuse same email for testing / diagnosis)

   d. Check Script output as it processes the reply email, prints out debug statements, and posts to Alation.

      Note: If you run the script with the piped syntax shown in step 2, all the script output will also be catured on a file on /tmp with prefix "process_reply_to_emails_output".

   e. (Optional: If there are any issues, please send Alation the script output for diagnosis)