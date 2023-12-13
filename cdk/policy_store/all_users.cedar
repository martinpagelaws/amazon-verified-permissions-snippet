permit (
	principal,
	action in [
		SimplePosts::Action::"GetAllPosts",
		SimplePosts::Action::"GetUserPosts",
		SimplePosts::Action::"CreatePost"
	],
	resource == SimplePosts::Application::"app"
);
