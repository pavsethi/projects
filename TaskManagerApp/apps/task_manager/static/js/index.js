var app = {};
app.config = {};
app.config.data = function() {
    return {
        unselected_tasks: [],
        selected_tasks: [],
        users: [],
        isSidebarActive: false,
        selectedFilter: '',
        filterParams: {},
		currentYear: new Date().getFullYear(),
		currentMonth: new Date().getMonth(),
		monthNames: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    };
};

app.config.computed = {};
app.config.computed.days = function() {
	const startOfMonth = new Date(this.currentYear, this.currentMonth, 1);
	const endOfMonth = new Date(this.currentYear, this.currentMonth + 1, 0);
	const daysArray = [];
	for (let day = startOfMonth; day <= endOfMonth; day.setDate(day.getDate() + 1)) {
		daysArray.push({ date: new Date(day) });
	}
	return daysArray;
}


app.config.methods = {};

app.config.methods.fetchUsers = function() {
    axios.get("/task_manager/api/users")
        .then(response => {
            console.log(response);
            app.vue.users = response.data.users; // Populate users array
        })
        .catch(error => {
            console.error('There was an error fetching the users:', error);
        });
}

app.config.methods.testapi = function() {
    axios.get("/tagged_posts/api/posts?tags=x,y,z")
}

app.config.methods.delpost = function(delid) {
    axios.delete("/tagged_posts/api/posts/" + delid).then(function() {
        app.vue.loaddata();
    });
}

app.config.methods.newtask = function() {
    window.location.href = '/create_task';
}

app.config.methods.loaddata = function() {
    axios.get("/task_manager/api/tasks").then(function(returnedtasks) {
        app.vue.unselected_tasks = returnedtasks["data"].tasks.map(task => ({
            ...task,
            comments: [],
            newComment: ''
        }));
        app.config.methods.loadComments(app.vue.unselected_tasks); 
    });

    app.config.methods.fetchUsers();
}


app.config.methods.loadComments = function(tasks) {
    tasks.forEach(task => {
        axios.get(`/task_manager/api/comments?task_id=${task.id}`)
            .then(response => {
                task.comments = response.data.comments;  
            })
            .catch(error => console.error("Failed to load comments for task " + task.id, error));
    });
}


app.config.methods.toggleSidebar = function() {
    this.isSidebarActive = !this.isSidebarActive;
}

app.config.methods.applyFilter = function() {
    console.log(app.vue.filterParams)
    let url = `/task_manager/api/filters/${this.selectedFilter}`;
    axios.get(url, { params: app.vue.filterParams })
    .then(response => {
        this.unselected_tasks = response.data.tasks;
        app.config.methods.loadComments(this.unselected_tasks); 
    })
    .catch(error => {
        console.error("There was an error applying the filter!", error);
    });
}


app.config.methods.editTask = function(taskId) {
    window.location.href = "/task_manager/edit_task/" + taskId;
}

app.config.methods.updateFilterParams = function(key, value) {
    console.log(key, value)
    this.filterParams[key] = value;
}

app.config.methods.submitComment = function(taskId) {
    let task = this.unselected_tasks.find(t => t.id === taskId);
    if (task.newComment.trim() !== '') {
        axios.post(`/task_manager/api/comments`, {
            task_id: taskId,
            content: task.newComment
        }).then(response => {
			console.log(response);
            task.comments.push({
                content: response.data.comment.comment.content,
                created_on: response.data.comment.comment.created_on,
                author: response.data.author
            });
			console.log(task.comments);
            task.newComment = '';
        }).catch(error => {
            console.error("Failed to post comment", error);
        });
    }
}

app.config.methods.prevMonth = function(){
	if (this.currentMonth === 0) {
		this.currentYear -= 1;
		this.currentMonth = 11;
	} else {
		this.currentMonth -= 1;
	}
}

app.config.methods.nextMonth = function(){
	if (this.currentMonth === 11) {
		this.currentYear += 1;
		this.currentMonth = 0;
	} else {
		this.currentMonth += 1;
	}
}

app.config.methods.hasTask = function(date) {
	const formatDate = d => dayjs(d).format('MM-DD-YYYY'); // formatting date using dayjs. Can't use regule Date() because it makes date one day less

    const dateString = formatDate(date);
    return this.unselected_tasks.some(task => formatDate(task.deadline) === dateString);
}

// app.config.methods.canEditTask = function(task) {
//     axios.get(`/api/can_edit_task/${task.id}`)
//         .then(response => {
//             if (response.data.can_edit) {
//                 // proceed to edit or show edit button
//                 task.canEdit = true;  // Assuming you have a canEdit property that controls the button display
//             } else {
//                 task.canEdit = false;
//             }
//         })
//         .catch(error => {
//             console.error("Error checking task edit permission", error);
//             task.canEdit = false;
//         });
// }

app.vue = Vue.createApp(app.config).mount("#app");
app.vue.loaddata();
