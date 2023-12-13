ACTIONS = {
    ("/", "GET"): "GetAllPosts",
    ("/posts", "GET"): "GetUserPosts",
    ("/posts", "POST"): "CreatePost",
    ("/posts/{postId}", "DELETE"): "DeletePost"
}
