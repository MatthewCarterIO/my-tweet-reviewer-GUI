"""
    File name: my_tweet_reviewer_GUI.py
    Author: Matthew Carter
    Date created: 01/06/2019
    Date last modified: 11/08/2019
    Python Version: 3.7.3
"""

import json
import pandas as pd
from os import path
import sys
import webbrowser
import tkinter as tk
from tkinter import messagebox


class MyTweetReviewerBase:
    # Colours.
    TEXT_LIGHT = "#FFFFFF"
    TEXT_DARK = "#000000"
    SHADE_ONE = "#C9FDC6"
    SHADE_TWO = "#A5D0A3"
    SHADE_THREE = "#6BA368"
    SHADE_FOUR = "#70785D"
    # Font.
    WINDOW_FONT_PATTERN = "*Font"
    WINDOW_FONT_VALUE = "Verdana"
    # Favicon.
    FAVICON = "mtr_favicon.ico"
    # Original tweet.js filename.
    TWEETJS_FILENAME = "tweet.js"

    # Window dimensions and name.
    window_w = 0
    window_h = 0
    window_name = " "

    def __init__(self, master, username, excluded_hashtags=None, saved_filename=None):
        self.root = master
        self.root.title(self.window_name)
        self.root.iconbitmap(self.FAVICON)
        self.root.geometry(self.central_window(self.root, self.window_w, self.window_h))
        self.root.resizable(0, 0)
        self.root.configure(background=self.SHADE_TWO)
        self.root.option_add(self.WINDOW_FONT_PATTERN, self.WINDOW_FONT_VALUE)
        self.username = username
        if excluded_hashtags is None:
            self.excluded_hashtags = []
        else:
            self.excluded_hashtags = excluded_hashtags
        if saved_filename is None:
            self.saved_filename = "my_tweet_review.csv"
        else:
            self.saved_filename = saved_filename
        self.tweets_df = self.load_df()

    # Calculate centre of screen and open window centrally.
    @staticmethod
    def central_window(window, window_width, window_height):
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        window_top_left_x = int((screen_width / 2) - (window_width / 2))
        window_top_left_y = int((screen_height / 2) - (window_height / 2))
        return "{}x{}+{}+{}".format(window_width, window_height, window_top_left_x, window_top_left_y)

    # Import the data from tweet.js.
    def import_raw_tweets_data(self):
        # Check tweet.js file exists in same folder as my_tweet_reviewer program and exit if it isn't found.
        if not path.exists(self.TWEETJS_FILENAME):
            self.tweetjs_missing_popup()
        with open(self.TWEETJS_FILENAME, mode='r', encoding="UTF-8") as raw_tweets_data:
            data = raw_tweets_data.read()
            # The data needed from tweet.js is contained within the first "[" and last "]".
            data = data[data.find('['): data.rfind(']') + 1]
        tweets_data = json.loads(data)
        # The tweet data comes as a list of dictionaries, each tweet being a dictionaryo of many key-value pairs.
        # For each tweet retrieve just the date of the tweet, tweet ID, tweet text and hashtags.
        tweets_list = []
        for tweet in tweets_data:
            # Date and ID.
            tweet_dict = {"tweet_created": tweet["created_at"], "tweet_id": tweet["id_str"]}
            # Text. Remove all special characters such as emojis because Tkinter has trouble displaying some of them.
            # Reduce the tweet into a string of only ASCII characters for simplicity.
            tweet_dict["tweet_text"] = tweet["full_text"].encode("UTF-8").decode("ascii", errors="ignore")
            # Hashtags. Add hashtags to dictionary only if the tweet contains them.
            tweet_hashtags = []
            for hashtag in tweet["entities"]["hashtags"]:
                tweet_hashtags.append(hashtag["text"])
            if len(tweet_hashtags):
                tweet_dict["tweet_hashtags"] = tweet_hashtags
            # Create complete tweet URL.
            tweet_dict["tweet_url"] = "https://twitter.com/" + self.username.strip('@') + "/status/" + tweet["id_str"]
            # Append tweet dictionary to tweets list.
            tweets_list.append(tweet_dict)
        # Return list of tweets.
        return tweets_list

    # Show tweet.js missing popup and exit program.
    @staticmethod
    def tweetjs_missing_popup():
        tk.messagebox.showerror(title="Missing File", message="The file tweet.js is not present in the same folder as "
                                                              "this program. Please address this and restart the "
                                                              "program.")
        sys.exit()

    # Create new DataFrame of tweets.
    @staticmethod
    def create_tweet_df(original_tweets_list):
        original_tweets_df = pd.DataFrame(original_tweets_list, columns=["tweet_created", "tweet_id", "tweet_text",
                                                                         "tweet_hashtags", "tweet_url"])
        # Convert created_at column of DataFrame to datetime format.
        original_tweets_df["tweet_created"] = pd.to_datetime(original_tweets_df["tweet_created"],
                                                             format='%a %b %d %H:%M:%S %z %Y')
        # Sort DataFrame by date, most recent first.
        original_tweets_df.sort_values(by=["tweet_created"], ascending=False, inplace=True)
        # Extract each hashtag into a column of its own.
        hashtag_df = original_tweets_df["tweet_hashtags"].apply(pd.Series).add_prefix("hashtag_")
        original_tweets_df = pd.concat([original_tweets_df, hashtag_df], axis=1)
        # Drop original hashtags column as it is no longer required.
        original_tweets_df.drop("tweet_hashtags", axis=1, inplace=True)
        # Add a tweet_review_status column to the DataFrame with default "none" values. This column will track the
        # tweets that have been reviewed.
        original_tweets_df["tweet_review_status"] = "none"
        # Add a tweet_url_visited column to the DataFrame with default "no" values. This column will track the tweets
        # that have been viewed in the browser.
        original_tweets_df["tweet_url_visited"] = "no"
        # Add a tweet_deleted column with default "no" values. This column will track the tweets that have been deleted
        # prior to their removal from the data.
        original_tweets_df["tweet_deleted"] = "no"
        # Return original DataFrame containing tweets.
        return original_tweets_df

    # Filter tweets DataFrame.
    def filter_tweets(self, original_df):
        # Get a list containing all hashtag column names in the DataFrame.
        df_col_names = original_df.columns.values.tolist()
        hashtag_col_names = []
        for col_name in df_col_names:
            if "hashtag_" in col_name:
                hashtag_col_names.append(col_name)
        # Create a new DataFrame with rows (tweets) removed if they contain any of the hashtags in the excluded hashtags
        # list.
        filtered_df = original_df.copy()
        for hashtag_col_name in hashtag_col_names:
            # Convert all hashtag columns to lowercase strings.
            filtered_df[hashtag_col_name] = filtered_df[hashtag_col_name].str.lower()
            # Remove rows from DataFrame if there are any hashtags in the exclusion list.
            if len(self.excluded_hashtags):
                filtered_df = filtered_df[~(filtered_df[hashtag_col_name].isin(self.excluded_hashtags))]
        # Return the filtered DataFrame.
        return filtered_df

    # Save DataFrame as CSV file.
    def save_df_as_csv(self):
        self.tweets_df.to_csv(self.saved_filename, index=None, header=True)

    # Show save DataFrame popup.
    def save_df_popup(self):
        save_decision = tk.messagebox.askyesno(title="Save", message="Would you like to save your progress and quit? "
                                                                     "This will overwrite any existing save file.")
        if save_decision == 1:
            tk.messagebox.showinfo(title="Save Completed", message="Progress was saved successfully.")
            self.save_df_as_csv()
        else:
            tk.messagebox.showinfo(title="Save Cancelled", message="Progress was not saved.")

    # Load existing or create new tweet DataFrame.
    def load_df(self):
        # Check if CSV exists.
        if path.exists(self.saved_filename):
            # Load existing CSV.
            tweets_df = pd.read_csv(self.saved_filename, header=0)
        else:
            # Import raw data and create new DataFrame.
            tweets = self.import_raw_tweets_data()
            tweets_df = self.create_tweet_df(tweets)
            tweets_df = self.filter_tweets(tweets_df)
        return tweets_df

    # Reset the review status, url visited and deleted columns in the DataFrame.
    def reset_df(self):
        # Ensure tweet_df is up to date by reloading the DataFrame prior to resetting columns (needed as main window is
        # not refreshed at any point).
        self.tweets_df = self.load_df()
        self.tweets_df["tweet_review_status"] = "none"
        self.tweets_df["tweet_url_visited"] = "no"
        self.tweets_df["tweet_deleted"] = "no"
        self.save_df_as_csv()
        return self.tweets_df

    # Show reset DataFrame popup.
    def reset_df_popup(self):
        # Open popup if there are tweets in the data.
        if len(self.tweets_df.index):
            reset_decision = tk.messagebox.askyesno(title="Reset", message="Reset the tweet_review_status, "
                                                                           "tweet_url_visited and "
                                                                           "tweet_deleted columns in the data?")
            if reset_decision == 1:
                tk.messagebox.showinfo(title="Reset Completed", message="Columns have been reset.")
                self.reset_df()
            else:
                tk.messagebox.showinfo(title="Reset Cancelled", message="Reset cancelled.")
        else:
            tk.messagebox.showinfo(title="No Data", message="There is currently no tweet data.")

    # Count total number of tweets.
    def count_total_tweets(self):
        number_total_tweets = len(self.tweets_df.index)
        return "Total Tweets: {}".format(number_total_tweets)


class MyTweetReviewer(MyTweetReviewerBase):
    # Main window dimensions and name.
    window_w = 300
    window_h = 300
    window_name = "My Tweet Reviewer"

    def __init__(self, master, username, excluded_hashtags=None, saved_filename=None):
        super().__init__(master, username, excluded_hashtags, saved_filename)
        # Main window text.
        self.greeting_label = tk.Label(self.root, text="Welcome to My Tweet Reviewer", bg=self.SHADE_TWO)
        self.greeting_label.grid(row=0, column=0, padx=15, pady=(20, 0))
        self.choice_label = tk.Label(self.root, text="What would you like to do?", bg=self.SHADE_TWO)
        self.choice_label.grid(row=1, column=0, padx=15, pady=(20, 0))
        # Main window buttons.
        self.home_buttons_frame = tk.Frame(self.root, bg=self.SHADE_TWO)
        self.home_buttons_frame.grid(row=2, column=0)
        self.review_tweets_btn = tk.Button(self.home_buttons_frame, text="Review Tweets", bg=self.SHADE_THREE,
                                           activebackground=self.SHADE_FOUR, width=14, height=1,
                                           command=self.open_review_window)
        self.review_tweets_btn.grid(row=0, column=0, padx=10, pady=(20, 10))
        self.delete_tweets_btn = tk.Button(self.home_buttons_frame, text="Delete Tweets", bg=self.SHADE_THREE,
                                           activebackground=self.SHADE_FOUR, width=14, height=1,
                                           command=self.open_delete_window)
        self.delete_tweets_btn.grid(row=1, column=0, padx=10, pady=(0, 10))
        self.reset_btn = tk.Button(self.home_buttons_frame, text="Reset", bg=self.SHADE_THREE,
                                   activebackground=self.SHADE_FOUR, width=14, height=1, command=self.reset_df_popup)
        self.reset_btn.grid(row=2, column=0, padx=10, pady=(0, 10))
        self.quit_btn = tk.Button(self.home_buttons_frame, text="Quit", bg=self.SHADE_THREE,
                                  activebackground=self.SHADE_FOUR, width=14, height=1,
                                  command=self.quit_mytweetreviewer)
        self.quit_btn.grid(row=3, column=0, padx=10, pady=(0, 10))

    # Open review tweets window.
    def open_review_window(self):
        # Open window if there are tweets in the data.
        if len(self.tweets_df.index):
            review_window_root = tk.Toplevel(self.root, background=self.SHADE_TWO)
            ReviewerReviewWindow(review_window_root, self.username, self.excluded_hashtags, self.saved_filename)
        else:
            tk.messagebox.showinfo(title="No Data", message="There is currently no tweet data.")

    # Open delete tweets window.
    def open_delete_window(self):
        # Open window if there are tweets in the data.
        if len(self.tweets_df.index):
            delete_window_root = tk.Toplevel(self.root, background=self.SHADE_TWO)
            ReviewerDeleteWindow(delete_window_root, self.username, self.excluded_hashtags, self.saved_filename)
        else:
            tk.messagebox.showinfo(title="No Data", message="There is currently no tweet data.")

    # Exit My Tweet Reviewer.
    def quit_mytweetreviewer(self):
        self.root.destroy()


class ReviewerReviewWindow(MyTweetReviewerBase):
    # Review tweets window dimensions and name.
    window_w = 500
    window_h = 540
    window_name = "Review Tweets"

    def __init__(self, master, username, excluded_hashtags=None, saved_filename=None):
        super().__init__(master, username, excluded_hashtags, saved_filename)
        # Ensure user can only interact with review tweets window while it is open but not the main window.
        self.root.grab_set()
        # Tracker which will become True if at least one tweet is reviewed.
        self.min_one_reviewed = False
        # Review window text.
        self.current_index = 0
        self.total_tweets_count = tk.StringVar()
        self.total_tweets_count.set(self.count_total_tweets())
        self.total_tweets_label = tk.Label(self.root, textvariable=self.total_tweets_count, bg=self.SHADE_TWO)
        self.total_tweets_label.grid(row=0, column=0, padx=15, pady=(20, 0))
        self.awaiting_review_count = tk.StringVar()
        self.awaiting_review_count.set(self.count_awaiting_review())
        self.awaiting_review_label = tk.Label(self.root, textvariable=self.awaiting_review_count, bg=self.SHADE_TWO)
        self.awaiting_review_label.grid(row=1, column=0, padx=15, pady=10)
        self.tweet_text = tk.StringVar()
        self.tweet_text.set("Click Next Tweet button to begin reviewing tweets.")
        self.tweet_text_label = tk.Label(self.root, width=47, height=10, bg=self.SHADE_ONE, justify="left",
                                         textvariable=self.tweet_text, wraplength=460)
        self.tweet_text_label.grid(row=2, column=0, padx=10, pady=10)
        # Review window buttons and radio buttons.
        self.review_status_frame = tk.LabelFrame(self.root, text="Review Status", background=self.SHADE_TWO,
                                                 labelanchor="n")
        self.review_status_frame.grid(row=3, column=0, padx=(10, 0), pady=10)
        self.rb_list = []
        self.rb_values = [("Keep", "keep", 0, 0), ("Delete", "delete", 0, 1), ("None", "none", 0, 2)]
        self.rb_review_status = tk.StringVar()
        self.rb_review_status.set("none")
        for rb_text, rb_value, grid_row, grid_col in self.rb_values:
            self.rb = tk.Radiobutton(self.review_status_frame, text=rb_text, value=rb_value,
                                     variable=self.rb_review_status, background=self.SHADE_TWO,
                                     activebackground=self.SHADE_TWO, command=self.update_review_btn_state,
                                     state="disabled")
            self.rb.grid(row=grid_row, column=grid_col)
            # Store radio buttons in list for enabling/disabling.
            self.rb_list.append(self.rb)
        self.update_review_btn = tk.Button(self.review_status_frame, text="Update", width=14, height=1,
                                           bg=self.SHADE_THREE, activebackground=self.SHADE_FOUR,
                                           command=self.update_review_clicked, state="disabled")
        self.update_review_btn.grid(row=0, column=3, padx=10, pady=10)
        self.review_buttons_frame = tk.Frame(self.root, background=self.SHADE_TWO)
        self.review_buttons_frame.grid(row=4, column=0)
        self.next_review_btn = tk.Button(self.review_buttons_frame, text="Next Tweet", width=14, height=1,
                                         bg=self.SHADE_THREE, activebackground=self.SHADE_FOUR,
                                         command=self.next_review_clicked)
        self.next_review_btn.grid(row=0, column=0, padx=10, pady=10)
        self.quit_review_btn = tk.Button(self.review_buttons_frame, text="Quit Reviewing", width=14, height=1,
                                         bg=self.SHADE_THREE, activebackground=self.SHADE_FOUR,
                                         command=self.quit_review_clicked)
        self.quit_review_btn.grid(row=1, column=0, padx=10, pady=(0, 10))

    # Count number of tweets awaiting review.
    def count_awaiting_review(self):
        awaiting_review = len(self.tweets_df[self.tweets_df["tweet_review_status"] == "none"])
        return "Awaiting Review: {}".format(awaiting_review)

    # Enable update button if a review status other than "none" has been selected using the radio buttons.
    def update_review_btn_state(self):
        if self.rb_review_status.get() == "none":
            self.update_review_btn["state"] = "disabled"
        else:
            self.update_review_btn["state"] = "normal"

    # Update the DataFrame with the selected review status from the radio buttons.
    def update_review_clicked(self):
        self.tweets_df.at[self.current_index, "tweet_review_status"] = self.rb_review_status.get()
        # After the update button has been clicked, disable the radio and update buttons to indicate to user that the
        # update has been done. Enable the next button to allow the user to go to the next tweet.
        for rb in self.rb_list:
            rb["state"] = "disabled"
        self.update_review_btn["state"] = "disabled"
        self.next_review_btn["state"] = "normal"
        # Update the counter label of tweets awaiting review.
        self.awaiting_review_count.set(self.count_awaiting_review())
        # Update the tracker to acknowledge at least one tweet has been reviewed, thereby activating the save option
        # upon quitting.
        self.min_one_reviewed = True

    # Move onto the next tweet for reviewing.
    def next_review_clicked(self):
        # Loop through DataFrame until the next tweet that hasn't been reviewed is found.
        for row_index, row in self.tweets_df.iterrows():
            if row["tweet_review_status"] == "none" and row_index >= self.current_index:
                # Reset the radio buttons.
                self.rb_review_status.set("none")
                # Set the tweet text.
                self.tweet_text.set(row["tweet_text"])
                # Update the current index with that of current tweet for use in updating DataFrame.
                self.current_index = row_index
                # Enable radio buttons and disable the next button until user has selected and updated review status
                # for the tweet.
                for rb in self.rb_list:
                    rb["state"] = "normal"
                self.next_review_btn["state"] = "disabled"
                break
            else:
                # No more tweets to review. Only the quit button remains active.
                self.tweet_text.set("No tweets to review.")
                self.next_review_btn["state"] = "disabled"

    # Exit review window.
    def quit_review_clicked(self):
        # If at least one tweet has been reviewed, offer the user a chance to save the DataFrame before closing the
        # review window.
        if self.min_one_reviewed:
            self.save_df_popup()
        self.root.destroy()


class ReviewerDeleteWindow(MyTweetReviewerBase):
    # Delete tweets window dimensions and name.
    window_w = 500
    window_h = 540
    window_name = "Delete Tweets"

    def __init__(self, master, username, excluded_hashtags=None, saved_filename=None):
        super().__init__(master, username, excluded_hashtags, saved_filename)
        # Ensure user can only interact with delete tweets window while it is open but not the main window.
        self.root.grab_set()
        # Tracker which will become True if at least one tweet is deleted.
        self.min_one_deleted = False
        # Delete window text.
        self.current_index = 0
        self.total_tweets_count = tk.StringVar()
        self.total_tweets_count.set(self.count_total_tweets())
        self.total_tweets_label = tk.Label(self.root, textvariable=self.total_tweets_count, bg=self.SHADE_TWO)
        self.total_tweets_label.grid(row=0, column=0, padx=15, pady=(20, 0))
        self.awaiting_deletion_count = tk.StringVar()
        self.awaiting_deletion_count.set(self.count_awaiting_deletion())
        self.awaiting_deletion_label = tk.Label(self.root, textvariable=self.awaiting_deletion_count, bg=self.SHADE_TWO)
        self.awaiting_deletion_label.grid(row=1, column=0, padx=15, pady=10)
        self.tweet_text = tk.StringVar()
        self.tweet_text.set("Click Next Tweet to begin deleting tweets.")
        self.tweet_text_label = tk.Label(self.root, width=47, height=10, bg=self.SHADE_ONE, justify="left",
                                         textvariable=self.tweet_text, wraplength=460)
        self.tweet_text_label.grid(row=2, column=0, padx=10, pady=10)
        # Delete window buttons and radio buttons.
        self.open_btn = tk.Button(self.root, text="Open In Browser", width=14, height=1, bg=self.SHADE_THREE,
                                  activebackground=self.SHADE_FOUR, command=self.open_delete_clicked,
                                  state="disabled")
        self.open_btn.grid(row=3, column=0, padx=10, pady=10)
        self.delete_status_frame = tk.LabelFrame(self.root, text="Mark As Deleted", background=self.SHADE_TWO,
                                                 labelanchor="n")
        self.delete_status_frame.grid(row=4, column=0, padx=10, pady=10)
        self.rb_list = []
        self.rb_values = [("Yes", "yes", 0, 0), ("No", "no", 0, 1)]
        self.rb_delete_status = tk.StringVar()
        self.rb_delete_status.set("no")
        for rb_text, rb_value, grid_row, grid_col in self.rb_values:
            self.rb = tk.Radiobutton(self.delete_status_frame, text=rb_text, value=rb_value,
                                     variable=self.rb_delete_status, background=self.SHADE_TWO,
                                     activebackground=self.SHADE_TWO, state="disabled")
            self.rb.grid(row=grid_row, column=grid_col, padx=10)
            # Store radio buttons in list for enabling/disabling.
            self.rb_list.append(self.rb)
        self.update_delete_btn = tk.Button(self.delete_status_frame, text="Update", width=14, height=1,
                                           bg=self.SHADE_THREE, activebackground=self.SHADE_FOUR,
                                           command=self.update_delete_clicked, state="disabled")
        self.update_delete_btn.grid(row=0, column=2, padx=10, pady=10)
        self.delete_buttons_frame = tk.Frame(self.root, background=self.SHADE_TWO)
        self.delete_buttons_frame.grid(row=5, column=0)
        self.next_delete_btn = tk.Button(self.delete_buttons_frame, text="Next Tweet", width=14, height=1,
                                         bg=self.SHADE_THREE, activebackground=self.SHADE_FOUR,
                                         command=self.next_delete_clicked)
        self.next_delete_btn.grid(row=0, column=0, padx=10, pady=10)
        self.quit_delete_btn = tk.Button(self.delete_buttons_frame, text="Quit Deleting", width=14, height=1,
                                         bg=self.SHADE_THREE, activebackground=self.SHADE_FOUR,
                                         command=self.quit_delete_clicked)
        self.quit_delete_btn.grid(row=1, column=0, padx=10, pady=(0, 10))

    # Count number of tweets awaiting deletion.
    def count_awaiting_deletion(self):
        awaiting_deletion = len(self.tweets_df[(self.tweets_df["tweet_review_status"] == "delete") &
                                               (self.tweets_df["tweet_url_visited"] == "no")])
        return "Awaiting Deletion: {}".format(awaiting_deletion)

    # Open tweet to be deleted in the browser.
    def open_delete_clicked(self):
        # Open tweet in browser.
        tweet_url = self.tweets_df["tweet_url"][self.current_index]
        webbrowser.open_new_tab(tweet_url)
        # Enable radio and update buttons after tweet is opened in browser.
        for rb in self.rb_list:
            rb["state"] = "normal"
        self.update_delete_btn["state"] = "normal"

    # Update the DataFrame with the selected deleted status from the radio buttons.
    def update_delete_clicked(self):
        # Update the tweet in the DataFrame as having been viewed in the browser. Note this update is not done when
        # open button itself is clicked because user may quit before choosing a delete status and updating, and the
        # tweet would not be shown again in delete window as it would have already been viewed.
        self.tweets_df.at[self.current_index, "tweet_url_visited"] = "yes"
        # Get result from radio button and update tweet_deleted column
        if self.rb_delete_status.get() == "yes":
            self.tweets_df.at[self.current_index, "tweet_deleted"] = "yes"
        # After the update button has been clicked, disable the open in browser, radio and update buttons to indicate
        # to user that the update has been done. Enable the next button to allow the user to go to the next tweet.
        self.open_btn["state"] = "disabled"
        for rb in self.rb_list:
            rb["state"] = "disabled"
        self.update_delete_btn["state"] = "disabled"
        self.next_delete_btn["state"] = "normal"
        # Update the counter label of tweets awaiting deletion.
        self.awaiting_deletion_count.set(self.count_awaiting_deletion())
        # Update the tracker to acknowledge at least one tweet has been deleted, thereby activating the save option
        # upon quitting.
        self.min_one_deleted = True

    # Move onto the next tweet for deleting.
    def next_delete_clicked(self):
        # Loop through DataFrame until the next tweet that hasn't been deleted is found.
        for row_index, row in self.tweets_df.iterrows():
            if row["tweet_review_status"] == "delete" and row["tweet_url_visited"] == "no":
                # Reset the radio buttons.
                self.rb_delete_status.set("no")
                # Set the tweet text.
                self.tweet_text.set(row["tweet_text"])
                # Update the current index with that of current tweet for use in updating DataFrame.
                self.current_index = row_index
                # Enable the open in browser button.
                self.open_btn["state"] = "normal"
                # Disable the update and next buttons until user has opened the tweet to delete in browser.
                self.update_delete_btn["state"] = "disabled"
                self.next_delete_btn["state"] = "disabled"
                break
            else:
                # No more tweets to open/delete. Only the quit button remains active.
                self.tweet_text.set("No tweets to delete.")
                self.next_delete_btn["state"] = "disabled"

    # Exit delete window.
    def quit_delete_clicked(self):
        # Loop through DataFrame and remove all rows of tweets that have been deleted. This is performed when the user
        # is ready to quit deleting and not when update button is clicked because the user may change mind and need to
        # reset the DataFrame (the tweets can't be recovered without a new DataFrame/save file being created from
        # tweet.js).
        for row_index, row in self.tweets_df.iterrows():
            if row["tweet_deleted"] == "yes":
                self.tweets_df.drop(row_index, inplace=True)
        # If at least one tweet has been deleted, offer the user a chance to save the DataFrame before closing the
        # delete window.
        if self.min_one_deleted:
            self.save_df_popup()
        self.root.destroy()


def main(username, excluded_hashtags=None, saved_filename=None):
    root = tk.Tk()
    MyTweetReviewer(root, username, excluded_hashtags, saved_filename)
    root.mainloop()


if __name__ == "__main__":
    # Enter the hashtags included in tweets you wish to remove from review process (without the '#').
    excluded_hashtags_list = ["hashtag1", "hashtag2", "hashtag3"]
    # Enter your Twitter username (including the '@'). The excluded_hashtags and saved_filename parameters are
    # optional.
    main("@yourusername", excluded_hashtags=excluded_hashtags_list, saved_filename="my_tweet_review.csv")
